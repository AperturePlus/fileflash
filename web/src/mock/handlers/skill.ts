import Mock from 'mockjs';
import { createMockId, getCurrentUser, mockSkills, paginate } from '../state';

type VisibilityFilter = 'all' | 'global' | 'private';

const now = () => new Date().toISOString();

const slugify = (input: string) => {
  return String(input || 'skill')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '') || 'skill';
};

const isAdmin = () => getCurrentUser().role === 'admin';

function isVisibleToUser(skill: any, userId: string, visibility: VisibilityFilter) {
  if (visibility === 'global') return skill.visibility === 'global';
  if (visibility === 'private') return skill.visibility === 'private' && skill.ownerUserId === userId;
  return skill.visibility === 'global' || (skill.visibility === 'private' && skill.ownerUserId === userId);
}

export const setupSkillMocks = () => {
  Mock.mock(/\/api\/v1\/agent\/skills(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const visibility = (url.searchParams.get('visibility') || 'all') as VisibilityFilter;
    const queryText = String(url.searchParams.get('queryText') || '').trim().toLowerCase();

    const user = getCurrentUser();
    const filtered = mockSkills
      .filter((skill) => isVisibleToUser(skill, user.userId, visibility))
      .filter((skill) => {
        if (!queryText) return true;
        const hay = `${skill.name} ${skill.description} ${skill.triggersText || ''} ${skill.skillKey}`.toLowerCase();
        return hay.includes(queryText);
      })
      .sort((a, b) => {
        if (a.visibility !== b.visibility) {
          return a.visibility === 'global' ? -1 : 1;
        }
        return String(b.createdAt || '').localeCompare(String(a.createdAt || ''));
      });

    const paged = paginate(filtered, page, perPage);
    return {
      success: true,
      code: 200,
      data: paged,
    };
  });

  Mock.mock(/\/api\/v1\/agent\/skills\/([^/]+)$/, 'get', (options) => {
    const raw = (options.url.match(/\/api\/v1\/agent\/skills\/([^/?]+)/) || [])[1];
    const skillKey = decodeURIComponent(String(raw || ''));
    const user = getCurrentUser();

    const skill = mockSkills.find((item) => item.skillKey === skillKey);
    if (!skill || !isVisibleToUser(skill, user.userId, 'all')) {
      return {
        success: false,
        code: 404,
        message: 'Skill not found',
        data: null,
      };
    }

    return {
      success: true,
      code: 200,
      data: skill,
    };
  });

  Mock.mock(/\/api\/v1\/agent\/skills$/, 'post', (options) => {
    const user = getCurrentUser();
    const payload = JSON.parse(options.body || '{}');
    const name = String(payload.name || '').trim();
    const description = String(payload.description || '').trim();

    if (!name || !description) {
      return {
        success: false,
        code: 400,
        message: 'Name and description are required',
        data: null,
      };
    }

    let key = '';
    for (let i = 0; i < 8; i += 1) {
      const suffix = Mock.Random.string('hex', 6);
      key = `user:${user.userId}:${slugify(name)}-${suffix}`;
      if (!mockSkills.some((item) => item.skillKey === key)) break;
    }

    const created: any = {
      skillId: createMockId('skill'),
      skillKey: key,
      name,
      description,
      triggersText: payload.triggersText ?? null,
      toolWhitelist: Array.isArray(payload.toolWhitelist) ? payload.toolWhitelist : [],
      planTemplate: payload.planTemplate || {},
      inputsSchema: payload.inputsSchema || {},
      outputsSchema: payload.outputsSchema || {},
      visibility: 'private',
      ownerUserId: user.userId,
      createdAt: now(),
      updatedAt: now(),
    };

    mockSkills.unshift(created);

    return {
      success: true,
      code: 201,
      message: 'Skill created successfully',
      data: created,
    };
  });

  Mock.mock(/\/api\/v1\/agent\/skills\/([^/]+)$/, 'patch', (options) => {
    const raw = (options.url.match(/\/api\/v1\/agent\/skills\/([^/?]+)/) || [])[1];
    const skillKey = decodeURIComponent(String(raw || ''));
    const user = getCurrentUser();
    const payload = JSON.parse(options.body || '{}');

    const skill = mockSkills.find((item) => item.skillKey === skillKey);
    if (!skill || skill.visibility !== 'private' || skill.ownerUserId !== user.userId) {
      return {
        success: false,
        code: 404,
        message: 'Skill not found',
        data: null,
      };
    }

    if (payload.name !== undefined) skill.name = String(payload.name || '').trim() || skill.name;
    if (payload.description !== undefined) skill.description = String(payload.description || '').trim() || skill.description;
    if (payload.triggersText !== undefined) skill.triggersText = payload.triggersText;
    if (payload.toolWhitelist !== undefined) skill.toolWhitelist = Array.isArray(payload.toolWhitelist) ? payload.toolWhitelist : [];
    if (payload.planTemplate !== undefined) skill.planTemplate = payload.planTemplate || {};
    if (payload.inputsSchema !== undefined) skill.inputsSchema = payload.inputsSchema || {};
    if (payload.outputsSchema !== undefined) skill.outputsSchema = payload.outputsSchema || {};
    skill.updatedAt = now();

    return {
      success: true,
      code: 200,
      data: skill,
    };
  });

  Mock.mock(/\/api\/v1\/agent\/skills\/([^/]+)$/, 'delete', (options) => {
    const raw = (options.url.match(/\/api\/v1\/agent\/skills\/([^/?]+)/) || [])[1];
    const skillKey = decodeURIComponent(String(raw || ''));
    const user = getCurrentUser();

    const index = mockSkills.findIndex((item) => item.skillKey === skillKey);
    const skill = index >= 0 ? mockSkills[index] : null;

    if (!skill || skill.visibility !== 'private' || skill.ownerUserId !== user.userId) {
      return {
        success: false,
        code: 404,
        message: 'Skill not found',
        data: null,
      };
    }

    mockSkills.splice(index, 1);

    return {
      success: true,
      code: 200,
      data: {
        skillKey,
        deletedAt: now(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/agent\/skills\/import$/, 'post', (options) => {
    if (!isAdmin()) {
      return {
        success: false,
        code: 403,
        message: 'Admin access required',
        data: null,
      };
    }

    const payload = JSON.parse(options.body || '{}');
    const mode = (payload.mode || 'upsert') as 'upsert' | 'insertOnly';
    const items = Array.isArray(payload.items) ? payload.items : [];

    if (!items.length) {
      return {
        success: false,
        code: 400,
        message: 'items is required',
        data: null,
      };
    }

    const conflicts: string[] = [];
    for (const item of items) {
      const key = String(item.skillKey || '').trim();
      const existing = mockSkills.find((s) => s.skillKey === key);
      if (!existing) continue;
      if (existing.visibility !== 'global') conflicts.push(key);
      else if (mode === 'insertOnly') conflicts.push(key);
    }

    if (conflicts.length) {
      return {
        success: false,
        code: 409,
        message: 'Skill key conflict',
        data: { conflicts },
      };
    }

    const results: Array<{ skillKey: string; action: 'created' | 'updated' }> = [];
    for (const item of items) {
      const skillKey = String(item.skillKey || '').trim();
      const name = String(item.name || '').trim();
      const description = String(item.description || '').trim();
      const existing = mockSkills.find((s) => s.skillKey === skillKey);

      if (!existing) {
        mockSkills.unshift({
          skillId: createMockId('skill'),
          skillKey,
          name,
          description,
          triggersText: item.triggersText ?? null,
          toolWhitelist: Array.isArray(item.toolWhitelist) ? item.toolWhitelist : [],
          planTemplate: item.planTemplate || {},
          inputsSchema: item.inputsSchema || {},
          outputsSchema: item.outputsSchema || {},
          visibility: 'global',
          ownerUserId: null,
          createdAt: now(),
          updatedAt: now(),
        });
        results.push({ skillKey, action: 'created' });
      } else {
        existing.name = name;
        existing.description = description;
        existing.triggersText = item.triggersText ?? null;
        existing.toolWhitelist = Array.isArray(item.toolWhitelist) ? item.toolWhitelist : [];
        existing.planTemplate = item.planTemplate || {};
        existing.inputsSchema = item.inputsSchema || {};
        existing.outputsSchema = item.outputsSchema || {};
        existing.updatedAt = now();
        results.push({ skillKey, action: 'updated' });
      }
    }

    return {
      success: true,
      code: 200,
      data: {
        results,
      },
    };
  });
};

