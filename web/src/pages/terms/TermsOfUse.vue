<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useLocaleStore } from '../../store/locale';
import { Divider, Surface } from '../../components/atoms';

const localeStore = useLocaleStore();
const { locale } = storeToRefs(localeStore);

const isZh = computed(() => locale.value === 'zh-CN');

const LAST_UPDATED = '2026-05-20';
</script>

<template>
  <div class="legal-page">
    <Surface elevation="raised" bordered class="legal-card">
      <header class="legal-header">
        <h1>{{ isZh ? '使用条款' : 'Terms of Use' }}</h1>
        <p class="legal-meta">
          {{ isZh ? `最后更新：${LAST_UPDATED}` : `Last updated: ${LAST_UPDATED}` }}
        </p>
      </header>

      <Divider />

      <div class="legal-content">
        <template v-if="isZh">
          <section>
            <h2>1. 接受与适用范围</h2>
            <p>欢迎使用 FileFlash（以下简称“本服务”）。本使用条款（以下简称“条款”）适用于你对本服务的访问与使用，包括我们提供的网页端、桌面端以及相关功能（如有）。</p>
            <p>当你访问、注册、登录或使用本服务，即表示你已阅读、理解并同意受本条款约束；若你不同意本条款，请不要使用本服务。</p>
          </section>

          <section>
            <h2>2. 账户、资格与安全</h2>
            <ul>
              <li>你应具备使用本服务所需的民事行为能力；如你未达到适用法律规定的年龄，应在监护人同意与指导下使用。</li>
              <li>你需要提供真实、准确、完整的注册信息，并在信息变更时及时更新。</li>
              <li>你应妥善保管账号与凭据（包括但不限于密码、访问令牌、设备登录态），并对在你账号下发生的所有活动负责。</li>
              <li>如发现未经授权的使用或安全漏洞，请尽快通过本服务内的支持渠道与我们联系。</li>
            </ul>
          </section>

          <section>
            <h2>3. 服务内容、变更与可用性</h2>
            <p>本服务可能包含文件上传、存储、下载、预览、分享、回收站、任务处理与自动化/Agent 工作流等能力。我们可能会持续迭代、更新或调整功能与界面，也可能出于安全、合规、稳定性或运营原因暂停或终止部分功能。</p>
            <p>我们会在合理范围内保持服务可用性，但不保证服务不会中断、不会出现错误或完全满足你的特定需求。</p>
          </section>

          <section>
            <h2>4. 使用规则与禁止行为</h2>
            <p>你同意仅以合法、合规且不侵犯他人权益的方式使用本服务。你不得：</p>
            <ul>
              <li>上传、存储、分享或传播违反法律法规、侵害他人合法权益（包括知识产权、隐私权）的内容。</li>
              <li>上传或传播恶意软件、木马、病毒，或以任何方式尝试破坏、干扰或绕过本服务的安全机制。</li>
              <li>对本服务进行反向工程、反编译、抓取（scraping）、未经授权的自动化访问，或以任何方式规避访问控制与配额限制。</li>
              <li>滥用分享链接（例如公开传播本应限制访问的链接），或以误导方式诱导他人访问分享内容。</li>
              <li>干扰其他用户正常使用，或对我们的基础设施造成不合理负载。</li>
            </ul>
          </section>

          <section>
            <h2>5. 你的内容（文件与数据）</h2>
            <p>你通过本服务上传、创建、存储或分享的文件、数据、文本、图片、音视频等内容（统称“你的内容”）仍归你或相应权利人所有。</p>
            <p>为了向你提供本服务，你授予我们一项在全球范围内、非独占的许可，使我们能够在提供服务所必需的范围内对你的内容进行托管、复制、传输、处理、格式转换/转码（如适用）、备份与展示，并按照你的设置向你授权的接收方提供访问。</p>
            <p>你声明并保证：你对你的内容拥有必要的权利、许可与授权，且你的内容与使用行为不违反任何法律法规与第三方权利。</p>
          </section>

          <section>
            <h2>6. 分享与协作</h2>
            <p>本服务可能支持通过分享链接或协作机制向他人开放访问。你理解并同意：</p>
            <ul>
              <li>你应对分享对象与分享范围负责；如果你将分享链接公开传播，任何持有链接的人可能访问相应内容。</li>
              <li>分享内容可能被接收方下载、复制或再次分享；请在分享前谨慎评估风险。</li>
            </ul>
          </section>

          <section>
            <h2>7. 存储、删除与备份提示</h2>
            <p>我们可能对存储空间、上传/下载速率、单次任务处理规模等进行限制，并可能根据套餐（如有）或系统策略调整。</p>
            <p>回收站与恢复等功能（如提供）旨在降低误删风险，但不构成对数据永久可恢复的保证。你应自行采取合理备份措施，对关键数据保留副本。</p>
          </section>

          <section>
            <h2>8. 费用与订阅（如适用）</h2>
            <p>部分功能或容量可能需要付费订阅或一次性购买（如适用）。如你选择付费，你同意按照购买页面或订单中展示的价格、计费周期与条款支付费用，并遵守我们不时更新的计费与退款规则（如有）。</p>
          </section>

          <section>
            <h2>9. 知识产权与反馈</h2>
            <p>除你的内容外，本服务及其相关软件、界面设计、商标标识、文档与代码等知识产权归我们或许可方所有。未经授权，你不得复制、修改、分发或创建衍生作品。</p>
            <p>如你向我们提供建议或反馈，你同意我们可在不向你支付费用且不承担保密义务的情况下使用该反馈来改进本服务。</p>
          </section>

          <section>
            <h2>10. 终止与违规处理</h2>
            <p>你可以停止使用本服务。我们也可能在合理判断你违反本条款、存在安全风险或法律合规要求时，限制、暂停或终止你对本服务的访问，并在必要时移除或限制相关内容。</p>
          </section>

          <section>
            <h2>11. 免责声明</h2>
            <p>在适用法律允许的最大范围内，本服务按“现状”和“可用”基础提供。我们不作任何明示或默示保证，包括但不限于适销性、特定用途适用性、非侵权以及持续可用性。</p>
          </section>

          <section>
            <h2>12. 责任限制</h2>
            <p>在适用法律允许的最大范围内，我们不对任何间接、附带、特殊、惩罚性或后果性损失承担责任，包括但不限于利润损失、业务中断、数据丢失或替代服务成本。</p>
            <p>在任何情况下，我们对因本服务或本条款引起的全部责任总额不超过你在引发索赔事件前 12 个月内为本服务实际支付的费用（如有）。如你未付费，则责任上限以适用法律允许的最低额度为限。</p>
          </section>

          <section>
            <h2>13. 赔偿</h2>
            <p>如因你对本服务的使用、你的内容、或你违反本条款而导致第三方向我们提出索赔、要求或损失，你同意在适用法律允许范围内为我们进行抗辩、赔偿并使我们免受损害。</p>
          </section>

          <section>
            <h2>14. 条款变更</h2>
            <p>我们可能不时更新本条款。若更新涉及重大变更，我们会通过合理方式提示（例如在应用内公告或更新页面日期）。更新生效后你继续使用本服务，视为你接受更新后的条款。</p>
          </section>

          <section>
            <h2>15. 适用法律与争议</h2>
            <p>本条款的解释与适用应遵循服务提供方设立地的法律（如适用法律另有强制规定，则从其规定）。因本条款产生的争议，双方应先友好协商解决；协商不成的，任一方可向有管辖权的法院提起诉讼。</p>
          </section>

          <section>
            <h2>16. 联系我们</h2>
            <p>如你对本条款有任何疑问，请通过本服务内提供的支持/反馈渠道与我们联系。</p>
          </section>

          <section>
            <h2>17. Agent / 自动化任务（专项）</h2>
            <p>本服务可能提供 Agent / 自动化任务能力，由你通过自然语言或预置技能（Skill）发起，并由本服务在你授权范围内代为执行一系列动作（例如读取/移动/重命名/删除文件等）。本节作为对前述条款的补充，规定 Agent 功能的使用规则。</p>
            <ul>
              <li><strong>17.1 执行策略。</strong>每次任务你可选择以下执行策略之一：<em>planOnly</em>（仅生成计划，不执行任何写动作）、<em>confirm</em>（生成计划后由你确认再执行）、<em>autopilot</em>（生成后自动执行）。在 autopilot 下，事先泛化授权的所有后果（包括不可逆操作）由你承担。</li>
              <li><strong>17.2 计划的不可改性（plan hash）。</strong>每个计划在生成时附带不可改的 planHash；执行时本服务校验 planHash 一致才会执行——即"你批准的就是被执行的"。任何在确认与执行之间对计划的修改都会导致执行被拒绝。</li>
              <li><strong>17.3 工具白名单与数据策略。</strong>Agent 只能调用对应 Skill 声明的工具白名单内的工具；可访问的数据范围受你在任务中传入的 dataPolicy 限制（例如是否允许读取文件内容、最大读取字节、允许的 MIME 类型等）。你理解上述限制可能影响任务结果质量。</li>
              <li><strong>17.4 资源消耗。</strong>Agent 任务可能消耗 token、调用次数、存储与计算资源，并可能受套餐或系统配额限制。任务可在执行中被你取消，但已发生的资源消耗不可撤销。</li>
              <li><strong>17.5 Skills 市场与自定义 Skill。</strong>全局 Skill 由部署方或管理员发布并审核；私有 Skill 由你自行创建、编辑、导入，其行为与合规性由你负责。请不要在 Skill 配置或 plan template 中包含敏感凭据、密钥或他人数据。导入他人提供的 Skill 前，请审阅其工具白名单与计划模板。</li>
              <li><strong>17.6 AI 服务提供方。</strong>本服务的 Agent 实现可能由部署方配置使用第三方 AI 服务（例如大型语言模型 API）。若启用，你的任务指令、相关上下文及（在你的 dataPolicy 允许范围内的）文件内容可能被传输至该 AI 服务方进行处理。具体提供方、所在地区与数据使用条款取决于部署，详见隐私政策第 13 节。</li>
              <li><strong>17.7 你对你批准的计划负责。</strong>Agent 执行的所有写动作均视为经你授权的操作。我们对因你批准的计划在你的内容上造成的结果（包括不可恢复的删除/移动/覆盖）不承担超出本条款责任限制范围的责任。对不可逆操作建议优先使用 confirm 策略。</li>
            </ul>
          </section>
        </template>

        <template v-else>
          <section>
            <h2>1. Acceptance and Scope</h2>
            <p>Welcome to FileFlash (the “Service”). These Terms of Use (the “Terms”) govern your access to and use of the Service, including our web app, desktop app, and related features (if any).</p>
            <p>By accessing, registering for, signing in to, or using the Service, you confirm that you have read, understood, and agree to be bound by these Terms. If you do not agree, do not use the Service.</p>
          </section>

          <section>
            <h2>2. Accounts, Eligibility, and Security</h2>
            <ul>
              <li>You must have the legal capacity required to use the Service. If you are below the age required by applicable law, you may use the Service only with a parent or guardian’s consent and supervision.</li>
              <li>You must provide accurate, complete, and up-to-date registration information, and keep it updated.</li>
              <li>You are responsible for safeguarding your account and credentials (including passwords, access tokens, and device sessions) and for all activities that occur under your account.</li>
              <li>If you believe your account has been compromised or used without authorization, contact us via the in-app support channel as soon as possible.</li>
            </ul>
          </section>

          <section>
            <h2>3. Service Features, Changes, and Availability</h2>
            <p>The Service may include capabilities such as file upload, storage, download, preview, sharing, recycle bin, background task processing, and automation/agent workflows. We may update, modify, suspend, or discontinue parts of the Service for security, compliance, reliability, or operational reasons.</p>
            <p>We strive to keep the Service available, but we do not guarantee uninterrupted or error-free operation, or that the Service will meet your specific requirements.</p>
          </section>

          <section>
            <h2>4. Acceptable Use and Prohibited Conduct</h2>
            <p>You agree to use the Service lawfully and in a way that does not infringe the rights of others. You must not:</p>
            <ul>
              <li>Upload, store, share, or distribute content that violates applicable laws or infringes third-party rights (including intellectual property and privacy rights).</li>
              <li>Upload or distribute malware, viruses, or attempt to disrupt, damage, bypass, or compromise the Service’s security mechanisms.</li>
              <li>Reverse engineer, decompile, scrape, or automate access without authorization, or circumvent access controls and quota limits.</li>
              <li>Abuse sharing links (for example, publicly distributing links intended for restricted access) or mislead others into accessing shared content.</li>
              <li>Interfere with other users’ access or impose an unreasonable load on our infrastructure.</li>
            </ul>
          </section>

          <section>
            <h2>5. Your Content</h2>
            <p>Files, data, text, images, audio/video, and other content you upload, create, store, or share through the Service (“Your Content”) remain owned by you or the applicable rights holders.</p>
            <p>To operate the Service, you grant us a worldwide, non-exclusive license to host, copy, transmit, process, transform/encode/transcode (where applicable), back up, and display Your Content to the extent necessary to provide the Service, and to make it available to recipients you authorize.</p>
            <p>You represent and warrant that you have all rights, licenses, and permissions necessary for Your Content and your use of the Service, and that your Content and activities do not violate applicable laws or third-party rights.</p>
          </section>

          <section>
            <h2>6. Sharing and Collaboration</h2>
            <p>The Service may allow you to share content via share links or collaboration features. You understand and agree that:</p>
            <ul>
              <li>You are responsible for selecting recipients and configuring access scope. If you share a link publicly, anyone with the link may access the content.</li>
              <li>Recipients may download, copy, or re-share content. Consider the risks before sharing.</li>
            </ul>
          </section>

          <section>
            <h2>7. Storage Limits, Deletion, and Backup Reminder</h2>
            <p>We may enforce limits on storage capacity, upload/download throughput, and task processing size, and may adjust such limits based on plan (if any) or system policies.</p>
            <p>Recycle bin and restore features (if provided) reduce the risk of accidental deletion but do not guarantee permanent recoverability. You should maintain your own backups for important data.</p>
          </section>

          <section>
            <h2>8. Fees and Subscriptions (If Applicable)</h2>
            <p>Certain features or capacity may require payment (if applicable). If you choose to pay, you agree to the pricing, billing cycle, and terms presented at purchase, and any billing/refund rules we may publish or update (if any).</p>
          </section>

          <section>
            <h2>9. Intellectual Property and Feedback</h2>
            <p>Except for Your Content, the Service and all related software, designs, trademarks, documentation, and code are owned by us or our licensors. You may not copy, modify, distribute, or create derivative works without authorization.</p>
            <p>If you submit feedback or suggestions, you agree we may use them to improve the Service without compensation and without any confidentiality obligation.</p>
          </section>

          <section>
            <h2>10. Suspension and Termination</h2>
            <p>You may stop using the Service at any time. We may restrict, suspend, or terminate your access if we reasonably believe you violated these Terms, pose a security risk, or as required by law, and may remove or restrict related content where necessary.</p>
          </section>

          <section>
            <h2>11. Disclaimers</h2>
            <p>To the maximum extent permitted by law, the Service is provided on an “as is” and “as available” basis. We disclaim all warranties, express or implied, including merchantability, fitness for a particular purpose, non-infringement, and availability.</p>
          </section>

          <section>
            <h2>12. Limitation of Liability</h2>
            <p>To the maximum extent permitted by law, we will not be liable for any indirect, incidental, special, punitive, or consequential damages, including lost profits, business interruption, loss of data, or costs of substitute services.</p>
            <p>In any event, our total liability arising out of or related to the Service or these Terms will not exceed the amounts you actually paid for the Service in the 12 months preceding the event giving rise to the claim (if any). If you did not pay, the liability cap will be the minimum allowed by applicable law.</p>
          </section>

          <section>
            <h2>13. Indemnification</h2>
            <p>To the extent permitted by law, you agree to defend, indemnify, and hold us harmless from claims, demands, losses, and liabilities arising out of your use of the Service, Your Content, or your violation of these Terms.</p>
          </section>

          <section>
            <h2>14. Changes to These Terms</h2>
            <p>We may update these Terms from time to time. If changes are material, we will provide reasonable notice (for example, via in-app notice or by updating the date on this page). Your continued use after the effective date constitutes acceptance of the updated Terms.</p>
          </section>

          <section>
            <h2>15. Governing Law and Disputes</h2>
            <p>These Terms are governed by the laws of the jurisdiction where the service provider is established, unless mandatory laws provide otherwise. Any dispute will first be resolved through good-faith negotiation; if unresolved, either party may bring a claim in a court of competent jurisdiction.</p>
          </section>

          <section>
            <h2>16. Contact</h2>
            <p>If you have any questions about these Terms, please contact us via the support/feedback channel available in the Service.</p>
          </section>

          <section>
            <h2>17. Agent / Automated Tasks (Supplemental)</h2>
            <p>The Service may provide Agent / automated-task capabilities, which you initiate via natural language or a preconfigured Skill and which the Service then executes on your behalf within the scope you authorize (for example: reading, moving, renaming, or deleting files). This section supplements the foregoing Terms and governs the use of Agent features.</p>
            <ul>
              <li><strong>17.1 Execution policy.</strong> For each task you may select one of the following execution policies: <em>planOnly</em> (generate a plan only, no write actions), <em>confirm</em> (generate a plan and execute only after you confirm), or <em>autopilot</em> (generate and execute automatically). Under autopilot, all consequences of pre-generalized authorization — including irreversible operations — are your responsibility.</li>
              <li><strong>17.2 Plan immutability (planHash).</strong> Each plan carries an immutable planHash at generation time. At execution, the Service verifies that the planHash matches — i.e., "what you approved is what gets executed." Any modification to a plan between approval and execution will cause execution to be rejected.</li>
              <li><strong>17.3 Tool whitelist and data policy.</strong> The Agent may only invoke tools listed in the corresponding Skill's tool whitelist. The data it can access is constrained by the dataPolicy you supply with each task (for example, whether file content may be read, the maximum read size in bytes, and allowed MIME types). You understand these constraints may affect task result quality.</li>
              <li><strong>17.4 Resource consumption.</strong> Agent tasks may consume tokens, tool-call counts, storage, and compute resources, and may be subject to plan or system quotas. A task can be canceled during execution, but resources already consumed are not refundable.</li>
              <li><strong>17.5 Skill marketplace and custom skills.</strong> Global Skills are published and reviewed by the deployer or administrators; private Skills are created, edited, and imported by you and you are responsible for their behavior and compliance. Do not include sensitive credentials, keys, or other parties' data in Skill configuration or plan templates. Review the tool whitelist and plan template of any third-party Skill before importing it.</li>
              <li><strong>17.6 AI service providers.</strong> The Agent implementation may, depending on deployer configuration, use third-party AI services (for example, large language model APIs). If enabled, your task instructions, related context, and (within your dataPolicy limits) file content may be transmitted to that AI service for processing. The specific provider, region, and data-handling terms depend on the deployment; see Privacy Policy §13 for details.</li>
              <li><strong>17.7 You are responsible for plans you approve.</strong> All write actions executed by the Agent are deemed authorized by you. We are not liable, beyond the limits in these Terms, for outcomes on Your Content resulting from plans you approved (including unrecoverable deletion, movement, or overwrite). For irreversible operations we recommend using the confirm policy.</li>
            </ul>
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
</style>
