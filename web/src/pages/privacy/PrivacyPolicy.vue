<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useLocaleStore } from '../../store/locale';
import { Divider, Surface } from '../../components/atoms';

const localeStore = useLocaleStore();
const { locale } = storeToRefs(localeStore);

const isZh = computed(() => locale.value === 'zh-CN');

const LAST_UPDATED = '2026-05-11';
</script>

<template>
  <div class="legal-page">
    <Surface elevation="raised" bordered class="legal-card">
      <header class="legal-header">
        <h1>{{ isZh ? '隐私政策' : 'Privacy Policy' }}</h1>
        <p class="legal-meta">
          {{ isZh ? `最后更新：${LAST_UPDATED}` : `Last updated: ${LAST_UPDATED}` }}
        </p>
      </header>

      <Divider />

      <div class="legal-content">
        <template v-if="isZh">
          <section>
            <h2>1. 本政策适用范围</h2>
            <p>本隐私政策说明 FileFlash（以下简称“我们”）在你使用本服务时，如何收集、使用、共享、保留与保护你的信息。本政策适用于我们提供的网页端、桌面端以及相关功能（如有）。</p>
          </section>

          <section>
            <h2>2. 我们收集的信息</h2>
            <p>根据你如何使用本服务，我们可能收集以下类别的信息：</p>
            <ul>
              <li><strong>账户信息</strong>：例如用户名、邮箱，以及用于认证与安全的相关信息（密码以加密/散列形式存储）。</li>
              <li><strong>你的内容与元数据</strong>：你上传/创建/存储的文件及其元数据，例如文件名、大小、类型、时间戳、目录结构、分享链接配置等。</li>
              <li><strong>使用与日志信息</strong>：例如访问时间、操作记录（上传、下载、分享、删除等）、错误日志、性能数据，以及用于安全审计与故障排查的信息。</li>
              <li><strong>设备与网络信息</strong>：例如设备类型、操作系统、浏览器类型、IP 地址等（用于安全与性能优化）。</li>
              <li><strong>Cookie 与类似技术</strong>：例如用于维持登录状态与安全的 Cookie（可能包含刷新令牌等），以及偏好设置相关的本地存储项。</li>
              <li><strong>沟通信息</strong>：你通过支持/反馈渠道提交的消息与附件（如有）。</li>
            </ul>
          </section>

          <section>
            <h2>3. 我们如何使用信息</h2>
            <p>我们通常会将你的信息用于以下目的：</p>
            <ul>
              <li>提供、维护与改进本服务（包括文件存储、分享、任务处理与自动化/Agent 功能）。</li>
              <li>进行身份验证、访问控制、风险识别、防欺诈与安全防护。</li>
              <li>进行客户支持、故障排查与服务通知（例如重要变更、系统维护）。</li>
              <li>遵守适用法律法规、响应合法请求与执行本条款。</li>
            </ul>
          </section>

          <section>
            <h2>4. 我们如何共享信息</h2>
            <p>我们不会在未经你授权的情况下向第三方披露你的内容，除非出现以下情形：</p>
            <ul>
              <li><strong>你主动共享</strong>：当你创建分享链接或授予他人访问权限时，相应接收方将能够访问你授权范围内的内容与元数据。</li>
              <li><strong>服务提供商</strong>：我们可能与提供托管、存储、发送邮件、监控与客户支持等服务的供应商共享必要信息，以便代表我们提供服务（受合同约束）。</li>
              <li><strong>合规与执法</strong>：为遵守法律义务、响应司法/执法请求、保护用户与公众安全、或维护我们合法权利时，我们可能披露必要信息。</li>
              <li><strong>企业/团队管理员</strong>：如你使用组织/团队账户，管理员可能在其权限范围内访问组织内的部分信息（例如账号与使用情况）。</li>
            </ul>
          </section>

          <section>
            <h2>5. Cookie 与登录状态</h2>
            <p>我们使用 Cookie 与类似技术来维持登录会话、提升安全性、保存偏好设置并帮助你更顺畅地使用本服务。你可以通过浏览器设置控制 Cookie，但部分功能在禁用 Cookie 后可能无法正常工作。</p>
          </section>

          <section>
            <h2>6. 数据保留与删除</h2>
            <p>我们会在实现本隐私政策所述目的所需的期限内保留信息。通常情况下：</p>
            <ul>
              <li>只要你的账户处于活动状态，我们会保留与你账户相关的必要信息与内容。</li>
              <li>当你删除内容或关闭账户后，我们可能在合理期限内从活跃系统中删除，但出于备份、审计、安全与合规要求，部分数据可能在更长时间内保留于备份或日志系统中。</li>
            </ul>
          </section>

          <section>
            <h2>7. 你的权利与选择</h2>
            <p>在适用法律允许范围内，你可以：</p>
            <ul>
              <li>访问、更新或更正你的账户信息。</li>
              <li>请求删除你的账户或内容（在满足合规与安全要求的前提下）。</li>
              <li>通过设置调整语言、主题等偏好，并控制部分权限与共享配置。</li>
            </ul>
          </section>

          <section>
            <h2>8. 安全</h2>
            <p>我们采取合理的技术与组织措施来保护信息安全（例如访问控制、传输加密、审计与监控等）。但任何系统都无法保证绝对安全，请你也采取适当措施保护账号安全。</p>
          </section>

          <section>
            <h2>9. 跨境传输（如适用）</h2>
            <p>根据你的所在地区与我们的基础设施部署，你的信息可能在你所在国家/地区之外进行处理。我们会采取合理措施，确保此类传输符合适用法律要求。</p>
          </section>

          <section>
            <h2>10. 儿童隐私</h2>
            <p>本服务并非面向儿童设计。若你认为未成年人在未经监护人同意的情况下向我们提供了个人信息，请通过本服务内的支持渠道联系我们以便处理。</p>
          </section>

          <section>
            <h2>11. 本政策变更</h2>
            <p>我们可能不时更新本隐私政策。若更新涉及重大变更，我们会通过合理方式提示（例如在应用内公告或更新页面日期）。</p>
          </section>

          <section>
            <h2>12. 联系我们</h2>
            <p>如你对本隐私政策有任何疑问或请求，请通过本服务内提供的支持/反馈渠道与我们联系。</p>
          </section>
        </template>

        <template v-else>
          <section>
            <h2>1. Scope</h2>
            <p>This Privacy Policy explains how FileFlash (“we”, “us”) collects, uses, shares, retains, and protects information when you use the Service. It applies to our web app, desktop app, and related features (if any).</p>
          </section>

          <section>
            <h2>2. Information We Collect</h2>
            <p>Depending on how you use the Service, we may collect the following categories of information:</p>
            <ul>
              <li><strong>Account information</strong>: such as your username, email address, and authentication/security-related information (passwords are stored in encrypted/hashed form).</li>
              <li><strong>Your content and metadata</strong>: files and data you upload/create/store, and related metadata such as file names, size, type, timestamps, folder structure, and sharing link configuration.</li>
              <li><strong>Usage and log information</strong>: such as access times, action logs (upload, download, share, delete), error logs, performance data, and information used for security auditing and troubleshooting.</li>
              <li><strong>Device and network information</strong>: such as device type, operating system, browser type, and IP address (used for security and performance optimization).</li>
              <li><strong>Cookies and similar technologies</strong>: used to maintain sessions and enhance security (may include refresh-token cookies), and preference-related local storage items.</li>
              <li><strong>Communications</strong>: messages and attachments you submit through our support/feedback channels (if any).</li>
            </ul>
          </section>

          <section>
            <h2>3. How We Use Information</h2>
            <p>We generally use information for the following purposes:</p>
            <ul>
              <li>Provide, maintain, and improve the Service (including file storage, sharing, task processing, and automation/agent features).</li>
              <li>Authenticate users, enforce access control, detect risks, prevent fraud, and protect security.</li>
              <li>Provide support, troubleshoot issues, and deliver service notices (such as important changes and maintenance).</li>
              <li>Comply with applicable laws, respond to lawful requests, and enforce our terms.</li>
            </ul>
          </section>

          <section>
            <h2>4. How We Share Information</h2>
            <p>We do not disclose Your Content to third parties without your authorization, except in the following situations:</p>
            <ul>
              <li><strong>You choose to share</strong>: when you create share links or grant access, recipients can access the content and metadata within the scope you authorize.</li>
              <li><strong>Service providers</strong>: we may share necessary information with vendors that provide hosting, storage, email delivery, monitoring, and support services on our behalf (subject to contractual restrictions).</li>
              <li><strong>Compliance and law enforcement</strong>: we may disclose information to comply with legal obligations, respond to lawful requests, protect users and public safety, or protect our rights.</li>
              <li><strong>Organization administrators</strong>: if you use an organization/team account, administrators may access certain information within their administrative privileges (for example, account and usage information).</li>
            </ul>
          </section>

          <section>
            <h2>5. Cookies and Sessions</h2>
            <p>We use cookies and similar technologies to maintain sessions, enhance security, store preferences, and help you use the Service smoothly. You can control cookies through your browser settings, but some features may not function properly if cookies are disabled.</p>
          </section>

          <section>
            <h2>6. Data Retention and Deletion</h2>
            <p>We retain information for as long as necessary to fulfill the purposes described in this Privacy Policy. In general:</p>
            <ul>
              <li>We retain necessary account information and content while your account is active.</li>
              <li>After you delete content or close your account, we may remove it from active systems within a reasonable time, but some data may persist longer in backups or logs for security, auditing, and compliance purposes.</li>
            </ul>
          </section>

          <section>
            <h2>7. Your Choices and Rights</h2>
            <p>To the extent permitted by applicable law, you may:</p>
            <ul>
              <li>Access, update, or correct your account information.</li>
              <li>Request deletion of your account or content (subject to compliance and security requirements).</li>
              <li>Use settings to manage preferences (language, theme) and control certain permissions and sharing configurations.</li>
            </ul>
          </section>

          <section>
            <h2>8. Security</h2>
            <p>We implement reasonable technical and organizational measures to protect information (for example, access controls, encryption in transit, auditing, and monitoring). However, no system can guarantee absolute security, and you should also protect your account.</p>
          </section>

          <section>
            <h2>9. International Transfers (If Applicable)</h2>
            <p>Depending on your location and our infrastructure, your information may be processed outside your country/region. We take reasonable steps to ensure such transfers comply with applicable law.</p>
          </section>

          <section>
            <h2>10. Children’s Privacy</h2>
            <p>The Service is not directed to children. If you believe a minor has provided personal information without appropriate consent, please contact us via the in-app support channel so we can address it.</p>
          </section>

          <section>
            <h2>11. Changes to This Policy</h2>
            <p>We may update this Privacy Policy from time to time. If changes are material, we will provide reasonable notice (for example, via in-app notice or by updating the date on this page).</p>
          </section>

          <section>
            <h2>12. Contact</h2>
            <p>If you have any questions or requests regarding this Privacy Policy, please contact us via the support/feedback channel available in the Service.</p>
          </section>
        </template>
      </div>
    </Surface>
  </div>
</template>

<style scoped>
.legal-page {
  width: min(960px, 92vw);
  max-height: calc(100vh - var(--sp-4xl));
}

.legal-card {
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: inherit;
}

.legal-header {
  padding: var(--sp-2xl);
}

.legal-header h1 {
  font-size: var(--text-h1);
  letter-spacing: var(--tracking-snug);
  line-height: var(--leading-snug);
}

.legal-meta {
  margin: var(--sp-xs) 0 0;
  color: var(--text-dim);
  font-size: var(--text-small);
}

.legal-content {
  padding: var(--sp-xl) var(--sp-2xl) var(--sp-2xl);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: var(--sp-xl);
}

.legal-content section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
}

.legal-content h2 {
  font-size: var(--text-h2);
  letter-spacing: var(--tracking-snug);
  line-height: var(--leading-snug);
}

.legal-content p {
  margin: 0;
  color: var(--text-secondary);
}

.legal-content ul {
  margin: 0;
  padding-left: 1.2em;
  color: var(--text-secondary);
}

.legal-content li {
  margin: var(--sp-xs) 0 0;
}

.legal-content li:first-child {
  margin-top: 0;
}

.legal-content strong {
  color: var(--text-primary);
}
</style>
