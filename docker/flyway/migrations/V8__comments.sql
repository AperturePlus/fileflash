-- =========================
-- Comments: table and column descriptions
-- =========================

COMMENT ON TABLE "user" IS '用户账户主表';
COMMENT ON COLUMN "user".user_id IS '用户主键';
COMMENT ON COLUMN "user".username IS '用户名（全局大小写不敏感唯一）';
COMMENT ON COLUMN "user".email IS '邮箱（全局大小写不敏感唯一）';
COMMENT ON COLUMN "user".password_hash IS '密码哈希';
COMMENT ON COLUMN "user".role IS '平台角色，例如 USER/ADMIN';
COMMENT ON COLUMN "user".status IS '账号状态';
COMMENT ON COLUMN "user".email_verified IS '邮箱是否已验证';
COMMENT ON COLUMN "user".storage_limit IS '存储配额（字节）';
COMMENT ON COLUMN "user".storage_used IS '已用空间（字节）';
COMMENT ON COLUMN "user".failed_login_count IS '连续登录失败次数';
COMMENT ON COLUMN "user".locked_until IS '账号锁定截止时间';

COMMENT ON TABLE user_preference IS 'User preference settings';
COMMENT ON COLUMN user_preference.preference_id IS 'Preference primary key';
COMMENT ON COLUMN user_preference.user_id IS 'User ID';
COMMENT ON COLUMN user_preference.ui_language IS 'UI language (zh-CN/en-US)';
COMMENT ON COLUMN user_preference.created_at IS 'Created timestamp';
COMMENT ON COLUMN user_preference.updated_at IS 'Updated timestamp';

COMMENT ON TABLE user_group IS '用户组定义';
COMMENT ON COLUMN user_group.id IS '用户组主键';
COMMENT ON COLUMN user_group.name IS '用户组名称';
COMMENT ON COLUMN user_group.description IS '用户组说明';

COMMENT ON TABLE user_group_member IS '用户组成员关系';
COMMENT ON COLUMN user_group_member.id IS '成员关系主键';
COMMENT ON COLUMN user_group_member.user_id IS '用户ID';
COMMENT ON COLUMN user_group_member.group_id IS '用户组ID';
COMMENT ON COLUMN user_group_member.role IS '组内角色';

COMMENT ON TABLE storage_object IS '物理存储对象（对象存储层）';
COMMENT ON COLUMN storage_object.object_id IS '对象主键';
COMMENT ON COLUMN storage_object.object_hash IS '对象内容哈希';
COMMENT ON COLUMN storage_object.hash_algorithm IS '哈希算法';
COMMENT ON COLUMN storage_object.bucket_name IS '对象存储桶名';
COMMENT ON COLUMN storage_object.object_key IS '对象存储键';
COMMENT ON COLUMN storage_object.object_size IS '对象大小（字节）';
COMMENT ON COLUMN storage_object.upload_status IS '上传与可用状态';
COMMENT ON COLUMN storage_object.scan_status IS '安全扫描状态';
COMMENT ON COLUMN storage_object.moderation_status IS '内容审核状态';
COMMENT ON COLUMN storage_object.ref_count IS '被逻辑文件引用计数';

COMMENT ON TABLE folder IS '文件夹目录节点';
COMMENT ON COLUMN folder.folder_id IS '目录主键';
COMMENT ON COLUMN folder.owner_id IS '目录所有者用户ID';
COMMENT ON COLUMN folder.parent_folder_id IS '父目录ID，根目录为NULL';
COMMENT ON COLUMN folder.folder_name IS '目录名';
COMMENT ON COLUMN folder.cached_size IS '缓存目录大小（字节）';
COMMENT ON COLUMN folder.status IS '目录状态';
COMMENT ON COLUMN folder.folder_type IS '目录类型（normal/root/system）';
COMMENT ON COLUMN folder.deleted_by IS '删除操作者用户ID';

COMMENT ON TABLE "file" IS '逻辑文件记录';
COMMENT ON COLUMN "file".file_id IS '文件主键';
COMMENT ON COLUMN "file".uploader_id IS '上传者用户ID';
COMMENT ON COLUMN "file".owner_id IS '文件所有者用户ID';
COMMENT ON COLUMN "file".folder_id IS '所在目录ID';
COMMENT ON COLUMN "file".file_name IS '文件名';
COMMENT ON COLUMN "file".mime_type IS 'MIME 类型';
COMMENT ON COLUMN "file".storage_object_id IS '关联物理对象ID';
COMMENT ON COLUMN "file".file_size IS '文件大小（字节）';
COMMENT ON COLUMN "file".status IS '文件状态';
COMMENT ON COLUMN "file".last_accessed_at IS '最后访问时间';

COMMENT ON TABLE acl IS '访问控制列表（文件/目录授权）';
COMMENT ON COLUMN acl.id IS 'ACL主键';
COMMENT ON COLUMN acl.file_id IS '授权文件ID';
COMMENT ON COLUMN acl.folder_id IS '授权目录ID';
COMMENT ON COLUMN acl.user_id IS '被授权用户ID';
COMMENT ON COLUMN acl.group_id IS '被授权用户组ID';
COMMENT ON COLUMN acl.permission_role IS '权限角色 viewer/editor/manager';
COMMENT ON COLUMN acl.can_preview IS '是否允许预览';
COMMENT ON COLUMN acl.can_download IS '是否允许下载';
COMMENT ON COLUMN acl.can_save IS '是否允许保存到我的网盘';
COMMENT ON COLUMN acl.can_share IS '是否允许继续分享';
COMMENT ON COLUMN acl.expire_at IS '授权过期时间';

COMMENT ON TABLE share IS '分享链接与分享策略';
COMMENT ON COLUMN share.share_id IS '分享主键';
COMMENT ON COLUMN share.user_id IS '分享发起人用户ID';
COMMENT ON COLUMN share.file_id IS '被分享文件ID';
COMMENT ON COLUMN share.folder_id IS '被分享目录ID';
COMMENT ON COLUMN share.share_link IS '兼容旧版的分享链接';
COMMENT ON COLUMN share.share_code IS '短分享码';
COMMENT ON COLUMN share.status IS '分享状态';
COMMENT ON COLUMN share.permission_role IS '分享默认权限角色';
COMMENT ON COLUMN share.allow_download IS '是否允许下载';
COMMENT ON COLUMN share.allow_save IS '是否允许保存到我的网盘';
COMMENT ON COLUMN share.require_login IS '访问是否要求登录';
COMMENT ON COLUMN share.expire_time IS '分享过期时间';
COMMENT ON COLUMN share.visit_count IS '访问次数';
COMMENT ON COLUMN share.download_count IS '下载次数';

COMMENT ON TABLE share_member IS '定向分享成员（用户或用户组）';
COMMENT ON COLUMN share_member.id IS '分享成员主键';
COMMENT ON COLUMN share_member.share_id IS '关联分享ID';
COMMENT ON COLUMN share_member.user_id IS '被分享用户ID';
COMMENT ON COLUMN share_member.group_id IS '被分享用户组ID';
COMMENT ON COLUMN share_member.status IS '接受状态';
COMMENT ON COLUMN share_member.target_folder_id IS '接受后落地目录ID';
COMMENT ON COLUMN share_member.accepted_at IS '接受时间';

COMMENT ON TABLE favorite_item IS '用户星标项';
COMMENT ON COLUMN favorite_item.favorite_id IS '星标主键';
COMMENT ON COLUMN favorite_item.user_id IS '用户ID';
COMMENT ON COLUMN favorite_item.item_type IS '星标项类型 file/folder';
COMMENT ON COLUMN favorite_item.file_id IS '星标文件ID';
COMMENT ON COLUMN favorite_item.folder_id IS '星标目录ID';

COMMENT ON TABLE user_folder_preference IS '用户目录视图偏好';
COMMENT ON COLUMN user_folder_preference.preference_id IS '偏好主键';
COMMENT ON COLUMN user_folder_preference.user_id IS '用户ID';
COMMENT ON COLUMN user_folder_preference.folder_id IS '目录ID，NULL表示全局默认';
COMMENT ON COLUMN user_folder_preference.view_mode IS '展示模式 list/grid';
COMMENT ON COLUMN user_folder_preference.sort_by IS '排序字段';
COMMENT ON COLUMN user_folder_preference.sort_direction IS '排序方向';

COMMENT ON TABLE "log" IS '审计日志';
COMMENT ON COLUMN "log".id IS '日志主键';
COMMENT ON COLUMN "log".user_id IS '操作用户ID（可为空）';
COMMENT ON COLUMN "log".actor_type IS '行为主体类型';
COMMENT ON COLUMN "log".operation IS '操作类型';
COMMENT ON COLUMN "log".target_type IS '目标资源类型';
COMMENT ON COLUMN "log".target_id IS '目标资源ID';
COMMENT ON COLUMN "log".result IS '操作结果';
COMMENT ON COLUMN "log".request_id IS '请求链路ID';

COMMENT ON TABLE notification IS '站内通知';
COMMENT ON COLUMN notification.id IS '通知主键';
COMMENT ON COLUMN notification.user_id IS '接收用户ID';
COMMENT ON COLUMN notification.type IS '通知业务类型';
COMMENT ON COLUMN notification.channel IS '发送渠道';
COMMENT ON COLUMN notification.message IS '通知正文';
COMMENT ON COLUMN notification.payload IS '扩展载荷(JSON)';
COMMENT ON COLUMN notification.is_read IS '是否已读';
COMMENT ON COLUMN notification.read_at IS '已读时间';
COMMENT ON COLUMN notification.sender_user_id IS '发送方用户ID';

COMMENT ON TABLE upload_task IS '上传任务';
COMMENT ON COLUMN upload_task.task_id IS '上传任务主键';
COMMENT ON COLUMN upload_task.user_id IS '任务所属用户ID';
COMMENT ON COLUMN upload_task.folder_id IS '目标目录ID';
COMMENT ON COLUMN upload_task.file_name IS '客户端文件名';
COMMENT ON COLUMN upload_task.total_size IS '文件总大小（字节）';
COMMENT ON COLUMN upload_task.chunk_size IS '分片大小（字节）';
COMMENT ON COLUMN upload_task.uploaded_bytes IS '已上传字节数';
COMMENT ON COLUMN upload_task.client_file_id IS '客户端幂等ID';
COMMENT ON COLUMN upload_task.status IS '上传任务状态';
COMMENT ON COLUMN upload_task.upload_id IS '多段上传会话ID';

COMMENT ON TABLE upload_task_part IS '上传任务分片';
COMMENT ON COLUMN upload_task_part.id IS '分片主键';
COMMENT ON COLUMN upload_task_part.task_id IS '上传任务ID';
COMMENT ON COLUMN upload_task_part.part_number IS '分片序号';
COMMENT ON COLUMN upload_task_part.part_size IS '分片大小（字节）';
COMMENT ON COLUMN upload_task_part.status IS '分片状态';
COMMENT ON COLUMN upload_task_part.checksum IS '分片校验值';
COMMENT ON COLUMN upload_task_part.retry_count IS '分片重试次数';

COMMENT ON TABLE password_reset_token IS '密码重置令牌';
COMMENT ON COLUMN password_reset_token.token_id IS '令牌主键';
COMMENT ON COLUMN password_reset_token.user_id IS '用户ID';
COMMENT ON COLUMN password_reset_token.token_hash IS '令牌哈希';
COMMENT ON COLUMN password_reset_token.expire_at IS '过期时间';
COMMENT ON COLUMN password_reset_token.used_at IS '使用时间';

COMMENT ON TABLE email_verification_token IS '邮箱验证令牌';
COMMENT ON COLUMN email_verification_token.token_id IS '令牌主键';
COMMENT ON COLUMN email_verification_token.user_id IS '用户ID';
COMMENT ON COLUMN email_verification_token.token_hash IS '令牌哈希';
COMMENT ON COLUMN email_verification_token.expire_at IS '过期时间';
COMMENT ON COLUMN email_verification_token.verified_at IS '验证完成时间';

COMMENT ON TABLE user_session IS '用户会话与刷新令牌';
COMMENT ON COLUMN user_session.session_id IS '会话主键';
COMMENT ON COLUMN user_session.user_id IS '用户ID';
COMMENT ON COLUMN user_session.refresh_token_hash IS '刷新令牌哈希';
COMMENT ON COLUMN user_session.client_type IS '客户端类型';
COMMENT ON COLUMN user_session.device_id IS '设备ID';
COMMENT ON COLUMN user_session.last_seen_at IS '最近活跃时间';
COMMENT ON COLUMN user_session.expire_at IS '会话过期时间';
COMMENT ON COLUMN user_session.revoked_at IS '会话吊销时间';

COMMENT ON TABLE file_preview_asset IS '文件预览产物';
COMMENT ON COLUMN file_preview_asset.preview_id IS '预览产物主键';
COMMENT ON COLUMN file_preview_asset.source_object_id IS '源对象ID';
COMMENT ON COLUMN file_preview_asset.preview_object_id IS '预览对象ID';
COMMENT ON COLUMN file_preview_asset.preview_type IS '预览类型';
COMMENT ON COLUMN file_preview_asset.page_no IS '页码（文档类）';
COMMENT ON COLUMN file_preview_asset.status IS '预览生成状态';

COMMENT ON TABLE file_media_metadata IS '媒体元数据';
COMMENT ON COLUMN file_media_metadata.metadata_id IS '媒体元数据主键';
COMMENT ON COLUMN file_media_metadata.source_object_id IS '源对象ID';
COMMENT ON COLUMN file_media_metadata.width IS '媒体宽度';
COMMENT ON COLUMN file_media_metadata.height IS '媒体高度';
COMMENT ON COLUMN file_media_metadata.duration_ms IS '时长（毫秒）';
COMMENT ON COLUMN file_media_metadata.extra_metadata IS '扩展元数据(JSON)';

COMMENT ON TABLE object_scan_result IS '对象扫描结果';
COMMENT ON COLUMN object_scan_result.scan_id IS '扫描记录主键';
COMMENT ON COLUMN object_scan_result.object_id IS '对象ID';
COMMENT ON COLUMN object_scan_result.scan_type IS '扫描类型';
COMMENT ON COLUMN object_scan_result.engine_name IS '扫描引擎名称';
COMMENT ON COLUMN object_scan_result.result IS '扫描结果';
COMMENT ON COLUMN object_scan_result.details IS '扫描明细(JSON)';

COMMENT ON TABLE moderation_case IS '内容审核工单';
COMMENT ON COLUMN moderation_case.case_id IS '工单主键';
COMMENT ON COLUMN moderation_case.object_id IS '对象ID';
COMMENT ON COLUMN moderation_case.file_id IS '关联文件ID';
COMMENT ON COLUMN moderation_case.reason_type IS '触发原因类型';
COMMENT ON COLUMN moderation_case.confidence IS '置信度';
COMMENT ON COLUMN moderation_case.status IS '工单状态';
COMMENT ON COLUMN moderation_case.resolution IS '处置结果';

COMMENT ON TABLE security_event IS '安全事件';
COMMENT ON COLUMN security_event.event_id IS '安全事件主键';
COMMENT ON COLUMN security_event.user_id IS '关联用户ID';
COMMENT ON COLUMN security_event.session_id IS '关联会话ID';
COMMENT ON COLUMN security_event.event_type IS '事件类型';
COMMENT ON COLUMN security_event.severity IS '风险级别';
COMMENT ON COLUMN security_event.occurred_at IS '事件发生时间';

COMMENT ON TABLE batch_download_task IS '批量下载打包任务';
COMMENT ON COLUMN batch_download_task.task_id IS '任务主键';
COMMENT ON COLUMN batch_download_task.user_id IS '用户ID';
COMMENT ON COLUMN batch_download_task.archive_name IS '压缩包文件名';
COMMENT ON COLUMN batch_download_task.item_count IS '打包条目数';
COMMENT ON COLUMN batch_download_task.items IS '打包条目清单(JSON)';
COMMENT ON COLUMN batch_download_task.status IS '任务状态';
COMMENT ON COLUMN batch_download_task.storage_object_id IS '生成压缩包对象ID';
COMMENT ON COLUMN batch_download_task.completed_at IS '完成时间';

COMMENT ON TABLE share_access_log IS '分享访问日志';
COMMENT ON COLUMN share_access_log.id IS '访问日志主键';
COMMENT ON COLUMN share_access_log.share_id IS '分享ID';
COMMENT ON COLUMN share_access_log.user_id IS '访问用户ID';
COMMENT ON COLUMN share_access_log.event_type IS '事件类型（visit/download）';
COMMENT ON COLUMN share_access_log.result IS '事件结果';
COMMENT ON COLUMN share_access_log.created_at IS '事件发生时间';

COMMENT ON VIEW v_file_folder_details IS '文件与目录统一列表视图';
COMMENT ON VIEW v_user_permissions IS '用户有效权限视图（直授+组授）';
COMMENT ON VIEW v_user_storage_summary IS '用户空间使用汇总视图';
COMMENT ON VIEW v_shared_with_me IS '共享给我的资源视图';
COMMENT ON VIEW v_full_path IS '目录全路径视图';
COMMENT ON VIEW v_user_recycle_bin IS '用户回收站视图';
COMMENT ON VIEW v_admin_share_overview IS '管理员分享总览视图';
COMMENT ON VIEW v_user_dashboard IS '管理员用户仪表盘视图';
COMMENT ON COLUMN background_job.agent_phase IS 'Agent runtime phase marker';
COMMENT ON COLUMN background_job.cancel_requested_at IS 'When the user requested cancellation';
