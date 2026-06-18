import { useState, useEffect } from 'react';
import { ConfigProvider, Layout, Drawer, Button, theme } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined, BulbOutlined, BulbFilled } from '@ant-design/icons';
import { useAgent } from './hooks/useAgent';
import AgentSidebar from './components/AgentSidebar';
import AgentChat from './components/AgentChat';
import AgentDetail from './components/AgentDetail';
import KnowledgeBase from './components/KnowledgeBase';
import Settings from './components/Settings';

const { Sider, Content } = Layout;

function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const handler = (e) => setMatches(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [query]);
  return matches;
}

export default function App() {
  const {
    filteredAgents,
    selectedAgentId,
    selectedAgent,
    conversations,
    activityLogs,
    stats,
    searchQuery,
    isThinking,
    selectAgent,
    toggleAgentStatus,
    clearConversation,
    refreshConversation,
    sendMessage,
    setSearchQuery,
  } = useAgent();

  const [detailOpen, setDetailOpen] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [kbOpen, setKbOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const isDesktop = useMediaQuery('(min-width: 1200px)');

  const currentMessages = selectedAgentId
    ? conversations[selectedAgentId] || []
    : [];
  const currentActivityLogs = selectedAgentId
    ? activityLogs[selectedAgentId] || []
    : [];

  const handleSendPreset = (prompt) => {
    if (selectedAgentId) {
      sendMessage(selectedAgentId, prompt);
    }
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <Layout className="agent-control-layout">
        {/* Left Sidebar */}
        <Sider
          width={280}
          style={{
            background: isDark ? '#141414' : '#fff',
            borderRight: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
            overflow: 'hidden',
          }}
        >
          <AgentSidebar
            filteredAgents={filteredAgents}
            selectedAgentId={selectedAgentId}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onSelectAgent={selectAgent}
            onToggleAgent={toggleAgentStatus}
            onOpenKnowledgeBase={() => setKbOpen(true)}
            stats={stats}
          />
        </Sider>

        {/* Center Chat */}
        <Content style={{ background: isDark ? '#1f1f1f' : '#fafafa' }}>
          <AgentChat
            agent={selectedAgent}
            messages={currentMessages}
            isThinking={isThinking}
            onSend={(content) => sendMessage(selectedAgentId, content)}
            onClear={(id) => clearConversation(id)}
            onRefresh={(id) => refreshConversation(id)}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        </Content>

        {/* Right Panel */}
        {isDesktop ? (
          <Sider
            width={320}
            collapsedWidth={0}
            collapsible
            collapsed={rightCollapsed}
            trigger={null}
            onCollapse={setRightCollapsed}
            style={{
              background: isDark ? '#141414' : '#fff',
              borderLeft: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
              overflow: 'hidden',
            }}
          >
            <div className="detail-toolbar">
              <Button
                type="text"
                icon={isDark ? <BulbFilled /> : <BulbOutlined />}
                onClick={() => setIsDark(!isDark)}
                size="small"
              />
              <Button
                type="text"
                icon={rightCollapsed ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
                onClick={() => setRightCollapsed(!rightCollapsed)}
                size="small"
              />
            </div>
            <AgentDetail
              agent={selectedAgent}
              activityLogs={currentActivityLogs}
              onSendPreset={handleSendPreset}
            />
          </Sider>
        ) : (
          <>
            <div className="mobile-floating-btns">
              <Button
                type="text"
                icon={isDark ? <BulbFilled /> : <BulbOutlined />}
                onClick={() => setIsDark(!isDark)}
                shape="circle"
              />
              <Button
                type="primary"
                icon={<MenuFoldOutlined />}
                onClick={() => setDetailOpen(true)}
                shape="circle"
              />
            </div>
            <Drawer
              open={detailOpen}
              onClose={() => setDetailOpen(false)}
              width={320}
              title="Agent 详情"
              styles={{ body: { padding: 0 } }}
            >
              <AgentDetail
                agent={selectedAgent}
                activityLogs={currentActivityLogs}
                onSendPreset={(prompt) => {
                  handleSendPreset(prompt);
                  setDetailOpen(false);
                }}
              />
            </Drawer>
          </>
        )}
      </Layout>
      <KnowledgeBase open={kbOpen} onClose={() => setKbOpen(false)} />
      <Settings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
      />
    </ConfigProvider>
  );
}
