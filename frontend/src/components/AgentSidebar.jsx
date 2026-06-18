import { useMemo } from 'react';
import { Input, Card, Badge, Switch, Tag, Empty, Avatar, Typography, Collapse, Button } from 'antd';
import {
  RobotOutlined,
  AppstoreOutlined,
  CodeOutlined,
  DatabaseOutlined,
  CustomerServiceOutlined,
  EditOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import StatsBar from './StatsBar';

const statusBadgeMap = {
  online: 'success',
  offline: 'default',
  error: 'error',
};

const categoryMeta = {
  general: { label: '通用', color: 'blue', icon: <AppstoreOutlined /> },
  development: { label: '开发', color: 'purple', icon: <CodeOutlined /> },
  data: { label: '数据', color: 'cyan', icon: <DatabaseOutlined /> },
  support: { label: '客服', color: 'orange', icon: <CustomerServiceOutlined /> },
  content: { label: '内容', color: 'green', icon: <EditOutlined /> },
};

function AgentCard({ agent, isSelected, onSelect, onToggle }) {
  return (
    <Card
      className={`agent-card${isSelected ? ' selected' : ''}`}
      hoverable
      size="small"
      onClick={() => onSelect(agent.id)}
    >
      <div className="agent-card-header">
        <div className="agent-card-info">
          <Badge status={statusBadgeMap[agent.status]} dot>
            <Avatar src={agent.avatar} icon={<RobotOutlined />} size={32} />
          </Badge>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="agent-name">
              <Typography.Text strong>{agent.name}</Typography.Text>
            </div>
            <div className="agent-desc">{agent.description}</div>
          </div>
        </div>
        <Switch
          checked={agent.status === 'online'}
          onChange={(checked, e) => {
            e.stopPropagation();
            onToggle(agent.id);
          }}
          size="small"
          onClick={(_, e) => e.stopPropagation()}
        />
      </div>
    </Card>
  );
}

export default function AgentSidebar({
  filteredAgents,
  selectedAgentId,
  searchQuery,
  onSearchChange,
  onSelectAgent,
  onToggleAgent,
  onOpenKnowledgeBase,
  stats,
}) {
  const groupedAgents = useMemo(() => {
    const groups = {};
    filteredAgents.forEach((agent) => {
      const cat = agent.category || 'general';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(agent);
    });
    return groups;
  }, [filteredAgents]);

  const collapseItems = Object.entries(groupedAgents).map(([category, agents]) => {
    const meta = categoryMeta[category] || { label: category, color: 'default', icon: null };
    return {
      key: category,
      label: (
        <span>
          {meta.icon}
          <span style={{ marginLeft: 8, fontWeight: 500 }}>{meta.label}</span>
          <Tag style={{ marginLeft: 8 }}>{agents.length}</Tag>
        </span>
      ),
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              isSelected={agent.id === selectedAgentId}
              onSelect={onSelectAgent}
              onToggle={onToggleAgent}
            />
          ))}
        </div>
      ),
    };
  });

  return (
    <div className="agent-sidebar">
      <StatsBar stats={stats} />
      <Input.Search
        placeholder="搜索 Agent..."
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        allowClear
      />
      <div className="agent-list">
        {collapseItems.length > 0 ? (
          <Collapse
            items={collapseItems}
            defaultActiveKey={Object.keys(groupedAgents)}
            ghost
            size="small"
          />
        ) : (
          <Empty description="未找到 Agent" style={{ marginTop: 60 }} />
        )}
      </div>

      <div className="sidebar-footer">
        <Button
          icon={<CloudUploadOutlined />}
          onClick={onOpenKnowledgeBase}
          block
          size="middle"
          type="default"
        >
          RAG 知识库
        </Button>
      </div>
    </div>
  );
}
