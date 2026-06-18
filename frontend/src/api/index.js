/**
 * API 模块统一导出
 *
 * 所有后端请求均在此处封装。
 * 当前为 mock 模式，对接后端时只需修改各模块中的 TODO 标注处。
 */

export { fetchAgents, fetchAgentById, updateAgentStatus } from './agents';
export { fetchConversations, sendMessage, clearConversations } from './conversations';
export { fetchActivities, addActivity } from './activities';
export { fetchKnowledgeFiles, uploadKnowledgeFile, deleteKnowledgeFile, retryIndexFile } from './knowledgeBase';
export { fetchUserProfile } from './user';
