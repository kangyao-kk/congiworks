import { useState, useEffect, useRef } from 'react';
import { Bubble, Sender, ThoughtChain } from '@ant-design/x';
import { Empty, Badge, Typography, Space, Button, Tooltip, Avatar, Dropdown } from 'antd';
import {
  ReloadOutlined,
  ClearOutlined,
  RobotOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';

const statusBadgeMap = {
  online: 'success',
  offline: 'default',
  error: 'error',
};

const statusLabelMap = {
  online: '在线',
  offline: '离线',
  error: '异常',
};

const userMenuItems = [
  { key: 'profile', icon: <UserOutlined />, label: '个人信息' },
  { key: 'settings', icon: <SettingOutlined />, label: '设置' },
  { type: 'divider' },
  { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
];

export default function AgentChat({ agent, messages, isThinking, onSend, onClear, onRefresh, onOpenSettings }) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  const handleMenuClick = ({ key }) => {
    if (key === 'settings') onOpenSettings?.();
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  if (!agent) {
    return (
      <div className="agent-chat">
        <div className="chat-header">
          <div className="chat-header-left">
            <Typography.Title level={5} style={{ margin: 0 }}>Agent 控制面板</Typography.Title>
          </div>
          <Dropdown menu={{ items: userMenuItems, onClick: handleMenuClick }} placement="bottomRight" trigger={['click']}>
            <Avatar
              size={32}
              icon={<UserOutlined />}
              src="https://api.dicebear.com/9.x/avataaars/svg?seed=admin"
              style={{ cursor: 'pointer', backgroundColor: '#1677ff' }}
            />
          </Dropdown>
        </div>
        <div className="chat-empty">
          <Empty description="选择一个 Agent 开始对话" />
        </div>
      </div>
    );
  }

  const handleSubmit = (value) => {
    if (!value.trim() || agent.status !== 'online') return;
    onSend(value.trim());
    setInputValue('');
  };

  const bubbleItems = messages.map((msg) => ({
    key: msg.id,
    placement: msg.role === 'user' ? 'end' : 'start',
    avatar: {
      src: msg.role === 'assistant'
        ? agent.avatar
        : undefined,
      icon: msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />,
    },
    content: msg.content,
  }));

  return (
    <div className="agent-chat">
      <div className="chat-header">
        <div className="chat-header-left">
          <Avatar src={agent.avatar} icon={<RobotOutlined />} size={28} />
          <Typography.Title level={5}>{agent.name}</Typography.Title>
          <Badge
            status={statusBadgeMap[agent.status]}
            text={statusLabelMap[agent.status]}
          />
        </div>
        <div className="chat-header-right">
          <Space>
            <Tooltip title="刷新">
              <Button icon={<ReloadOutlined />} size="small" onClick={() => onRefresh?.(agent.id)} />
            </Tooltip>
            <Tooltip title="清空对话">
              <Button icon={<ClearOutlined />} size="small" onClick={() => onClear?.(agent.id)} />
            </Tooltip>
          </Space>
          <Dropdown menu={{ items: userMenuItems, onClick: handleMenuClick }} placement="bottomRight" trigger={['click']}>
            <Avatar
              size={32}
              icon={<UserOutlined />}
              src="https://api.dicebear.com/9.x/avataaars/svg?seed=admin"
              style={{ cursor: 'pointer', backgroundColor: '#1677ff' }}
            />
          </Dropdown>
        </div>
      </div>

      <div className="chat-messages">
        <Bubble.List
          items={bubbleItems}
          style={{ maxWidth: 800, margin: '0 auto' }}
        />
        {isThinking && (
          <div style={{ maxWidth: 800, margin: '0 auto', padding: '8px 0' }}>
            <ThoughtChain
              items={[
                {
                  key: 'thinking',
                  status: 'loading',
                  title: '思考中...',
                  description: 'Agent 正在处理您的请求',
                },
              ]}
            />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <Sender
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          placeholder={`向 ${agent.name} 发送消息...`}
          loading={isThinking}
          disabled={agent.status !== 'online'}
        />
      </div>
    </div>
  );
}
