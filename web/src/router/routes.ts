import type { RouteRecordRaw } from "vue-router";
import MainLayout from "../components/templates/MainLayout.vue";
import AuthLayout from "../components/templates/AuthLayout.vue";
import BareLayout from "../components/templates/BareLayout.vue";
import ShareLayout from "../components/templates/ShareLayout.vue";
import AgentLayout from "../components/templates/AgentLayout.vue";

const devRoutes: Array<RouteRecordRaw> = import.meta.env.DEV
  ? [
      {
        path: "/__dev/library",
        name: "DevLibrary",
        component: () => import("../pages/__dev/index.ts"),
        meta: { requiresAuth: false },
      },
    ]
  : [];

export const routes: Array<RouteRecordRaw> = [
  ...devRoutes,
  {
    path: "/terms",
    name: "TermsOfService",
    component: BareLayout,
    children: [
      { path: "", component: () => import("../pages/terms/index.ts") },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/privacy",
    name: "PrivacyPolicy",
    component: BareLayout,
    children: [
      { path: "", component: () => import("../pages/privacy/index.ts") },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/login",
    name: "Login",
    component: AuthLayout,
    children: [
      { path: "", component: () => import("../pages/login/index.ts") },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/register",
    name: "Register",
    component: AuthLayout,
    children: [
      { path: "", component: () => import("../pages/register/index.ts") },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/forgot-password",
    name: "ForgotPassword",
    component: AuthLayout,
    children: [
      {
        path: "",
        component: () => import("../pages/forgot-password/index.ts"),
      },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/verify-email",
    name: "VerifyEmail",
    component: BareLayout,
    children: [
      { path: "", component: () => import("../pages/verify-email/index.ts") },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/share/:shareLink",
    name: "ShareAccess",
    component: ShareLayout,
    children: [
      { path: "", component: () => import("../pages/share/index.ts") },
    ],
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    name: "Home",
    component: MainLayout,
    redirect: "/files",
    meta: { requiresAuth: true },
    children: [
      {
        path: "files",
        name: "MyFiles",
        component: () => import("../pages/files/index.ts"),
        meta: { navId: "my-files" },
      },
      {
        path: "shared",
        name: "Shared",
        component: () => import("../pages/shared/index.ts"),
        meta: { navId: "shared" },
      },
      {
        path: "trash",
        name: "Trash",
        component: () => import("../pages/trash/index.ts"),
        meta: { navId: "trash" },
      },
      {
        path: "profile",
        name: "Profile",
        component: () => import("../pages/profile/index.ts"),
        meta: { navId: "profile" },
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("../pages/settings/index.ts"),
        meta: { navId: "settings" },
      },
      {
        path: "dashboard",
        redirect: "/console/overview",
      },
      {
        path: "console",
        component: () => import("../pages/console/ConsoleLayout.vue"),
        meta: { navId: "console", requiresAdmin: true },
        children: [
          { path: "", redirect: "/console/overview" },
          {
            path: "overview",
            name: "ConsoleOverview",
            component: () => import("../pages/console/overview/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "users",
            name: "ConsoleUsers",
            component: () => import("../pages/console/users/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "storage",
            name: "ConsoleStorage",
            component: () => import("../pages/console/storage/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "content",
            name: "ConsoleContent",
            component: () => import("../pages/console/content/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "moderation",
            name: "ConsoleModeration",
            component: () => import("../pages/console/moderation/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "system",
            name: "ConsoleSystem",
            component: () => import("../pages/console/system/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "logs",
            name: "ConsoleLogs",
            component: () => import("../pages/console/logs/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "notifications",
            name: "ConsoleNotifications",
            component: () => import("../pages/console/notifications/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
          {
            path: "rules",
            name: "ConsoleRules",
            component: () => import("../pages/console/rules/index.ts"),
            meta: { navId: "console", requiresAdmin: true },
          },
        ],
      },
      {
        path: "agent",
        component: AgentLayout,
        meta: { navId: "agent" },
        children: [
          {
            path: "",
            name: "AgentWorkspace",
            component: () => import("../pages/agent/workspace/index.ts"),
            meta: { navId: "agent" },
          },
          {
            path: "skills",
            name: "AgentSkills",
            component: () => import("../pages/agent/skills/index.ts"),
            meta: { navId: "agent" },
          },
        ],
      },
    ],
  },
  { path: "/skills", name: "SkillsLegacy", redirect: "/agent/skills" },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    redirect: "/",
  },
];
