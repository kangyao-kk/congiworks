import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  fetchAgents,
  fetchAgentById,
  updateAgentStatus,
  fetchConversations,
  sendMessage,
  clearConversations,
  fetchActivities,
  addActivity,
} from '../api';

export function useAgent() {
  const [agents, setAgents] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [conversations, setConversations] = useState({});
  const [activityLogs, setActivityLogs] = useState({});
  const [isThinking, setIsThinking] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [agentList] = await Promise.all([fetchAgents()]);
        setAgents(agentList);
        if (agentList.length > 0) {
          const firstId = agentList[0].id;
          const [convs, acts] = await Promise.all([
            fetchConversations(firstId),
            fetchActivities(firstId),
          ]);
          setConversations({ [firstId]: convs });
          setActivityLogs({ [firstId]: acts });
        }
      } catch (err) {
        console.error('加载数据失败:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === selectedAgentId) || null,
    [agents, selectedAgentId]
  );

  const filteredAgents = useMemo(
    () =>
      agents.filter(
        (a) =>
          a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          a.description.toLowerCase().includes(searchQuery.toLowerCase())
      ),
    [agents, searchQuery]
  );

  const stats = useMemo(
    () => ({
      total: agents.length,
      online: agents.filter((a) => a.status === 'online').length,
      offline: agents.filter((a) => a.status === 'offline').length,
    }),
    [agents]
  );

  const selectAgent = useCallback(
    async (id) => {
      setSelectedAgentId(id);
      if (!conversations[id]) {
        const convs = await fetchConversations(id);
        setConversations((prev) => ({ ...prev, [id]: convs }));
      }
      if (!activityLogs[id]) {
        const acts = await fetchActivities(id);
        setActivityLogs((prev) => ({ ...prev, [id]: acts }));
      }
    },
    [conversations, activityLogs]
  );

  const toggleAgentStatus = useCallback(async (id) => {
    const agent = agents.find((a) => a.id === id);
    if (!agent) return;
    const newStatus = agent.status === 'online' ? 'offline' : 'online';

    await updateAgentStatus(id, newStatus);

    setAgents((prev) =>
      prev.map((a) =>
        a.id === id ? { ...a, status: newStatus, lastActive: new Date().toISOString() } : a
      )
    );

    const act = await addActivity(id, {
      type: newStatus === 'online' ? 'agent_started' : 'agent_stopped',
      description: `${agent.name} ${newStatus === 'online' ? '已上线' : '已下线'}`,
    });
    setActivityLogs((prev) => ({
      ...prev,
      [id]: [act, ...(prev[id] || [])],
    }));
  }, [agents]);

  const handleSendMessage = useCallback(
    async (agentId, content) => {
      const agent = agents.find((a) => a.id === agentId);
      if (!agent || agent.status !== 'online') return;

      setIsThinking(true);

      // 用户消息立即加入对话
      const userMsg = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      // 占位 AI 消息（随 token 实时更新）
      const streamId = `msg-${Date.now()}-assistant`;
      const streamMsg = {
        id: streamId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      };

      setConversations((prev) => ({
        ...prev,
        [agentId]: [...(prev[agentId] || []), userMsg, streamMsg],
      }));

      try {
        const { userMsg: confirmedUser, aiMsg } = await sendMessage(
          agentId,
          content,
          (token) => {
            // 每收到一个 token，更新流式消息
            setConversations((prev) => {
              const msgs = [...(prev[agentId] || [])];
              for (let i = msgs.length - 1; i >= 0; i--) {
                if (msgs[i].id === streamId) {
                  msgs[i] = { ...msgs[i], content: msgs[i].content + token };
                  break;
                }
              }
              return { ...prev, [agentId]: msgs };
            });
          }
        );

        // 流结束，补充 thinking 元数据（content 已由 token 完成）
        setConversations((prev) => {
          const msgs = [...(prev[agentId] || [])];
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].id === streamId) {
              msgs[i] = { ...msgs[i], thinking: aiMsg.thinking };
              break;
            }
          }
          return { ...prev, [agentId]: msgs };
        });

        // 刷新活动日志和 Agent 指标
        const acts = await fetchActivities(agentId);
        setActivityLogs((prev) => ({ ...prev, [agentId]: acts }));

        const updatedAgent = await fetchAgentById(agentId);
        if (updatedAgent) {
          setAgents((prev) =>
            prev.map((a) => (a.id === agentId ? updatedAgent : a))
          );
        }
      } catch (err) {
        console.error('发送消息失败:', err);
        // 移除占位消息
        setConversations((prev) => {
          const msgs = (prev[agentId] || []).filter((m) => m.id !== streamId);
          return { ...prev, [agentId]: msgs };
        });
        try {
          await addActivity(agentId, {
            type: 'error_occurred',
            description: `消息发送失败: ${err.message}`,
          });
        } catch {}
      } finally {
        setIsThinking(false);
      }
    },
    [agents]
  );

  const handleClearConversation = useCallback(
    async (agentId) => {
      try {
        await clearConversations(agentId);
      } catch {}
      setConversations((prev) => ({ ...prev, [agentId]: [] }));
    },
    []
  );

  const handleRefreshConversation = useCallback(
    async (agentId) => {
      try {
        const convs = await fetchConversations(agentId);
        setConversations((prev) => ({ ...prev, [agentId]: convs }));
      } catch {}
    },
    []
  );

  return {
    agents,
    selectedAgentId,
    selectedAgent,
    filteredAgents,
    conversations,
    activityLogs,
    stats,
    searchQuery,
    isThinking,
    loading,
    selectAgent,
    toggleAgentStatus,
    clearConversation: handleClearConversation,
    refreshConversation: handleRefreshConversation,
    sendMessage: handleSendMessage,
    setSearchQuery,
  };
}
