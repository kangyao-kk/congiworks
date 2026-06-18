import { useState } from 'react';
import { Drawer, Switch, Typography, Input, Button, message, Avatar, Form } from 'antd';
import {
  BulbOutlined,
  UserOutlined,
  BellOutlined,
  BankOutlined,
  MailOutlined,
  GlobalOutlined,
  EditOutlined,
} from '@ant-design/icons';

const { Text } = Typography;
const { TextArea } = Input;

const mockCompany = {
  name: 'Agency 智能科技',
  description: '专注于 AI Agent 平台研发，提供 RAG 知识库、双重记忆、Skill 插件等核心能力，帮助企业快速构建智能助手。',
  website: 'https://agency.local',
};

export default function Settings({ open, onClose, isDark, onToggleTheme }) {
  const [userName, setUserName] = useState('管理员');
  const [userEmail, setUserEmail] = useState('admin@agency.local');
  const [companyName, setCompanyName] = useState(mockCompany.name);
  const [companyDesc, setCompanyDesc] = useState(mockCompany.description);
  const [companyWebsite, setCompanyWebsite] = useState(mockCompany.website);
  const [notifyTask, setNotifyTask] = useState(true);
  const [notifyError, setNotifyError] = useState(true);

  const handleSave = () => {
    message.success('设置已保存（仅当前会话生效）');
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={420}
      title={null}
      footer={
        <div className="settings-footer">
          <Button type="primary" block size="large" onClick={handleSave}>
            保存设置
          </Button>
        </div>
      }
      styles={{ body: { padding: 0 } }}
    >
      <div className="settings-content">
        {/* 用户信息 */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="settings-card-icon settings-card-icon--user">
              <UserOutlined />
            </div>
            <div>
              <Text strong style={{ fontSize: 16 }}>用户信息</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>编辑您的个人资料</Text>
            </div>
          </div>
          <div className="settings-card-body">
            <div className="settings-avatar-row">
              <Avatar
                size={64}
                icon={<UserOutlined />}
                src="https://api.dicebear.com/9.x/avataaars/svg?seed=admin"
                style={{ backgroundColor: '#1677ff' }}
              />
              <div className="settings-avatar-info">
                <Text strong style={{ fontSize: 15 }}>{userName}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>{userEmail}</Text>
              </div>
            </div>
            <div className="settings-field">
              <div className="settings-field-label">
                <UserOutlined style={{ color: '#1677ff' }} />
                <Text style={{ fontSize: 13 }}>用户名</Text>
              </div>
              <Input
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="请输入用户名"
                prefix={<EditOutlined style={{ color: '#bfbfbf' }} />}
              />
            </div>
            <div className="settings-field">
              <div className="settings-field-label">
                <MailOutlined style={{ color: '#1677ff' }} />
                <Text style={{ fontSize: 13 }}>邮箱</Text>
              </div>
              <Input
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                placeholder="请输入邮箱"
                prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
              />
            </div>
          </div>
        </div>

        {/* 公司信息 */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="settings-card-icon settings-card-icon--company">
              <BankOutlined />
            </div>
            <div>
              <Text strong style={{ fontSize: 16 }}>公司信息</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>管理您的企业资料</Text>
            </div>
          </div>
          <div className="settings-card-body">
            <div className="settings-field">
              <div className="settings-field-label">
                <BankOutlined style={{ color: '#722ed1' }} />
                <Text style={{ fontSize: 13 }}>公司名称</Text>
              </div>
              <Input
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="请输入公司名称"
              />
            </div>
            <div className="settings-field">
              <div className="settings-field-label">
                <EditOutlined style={{ color: '#722ed1' }} />
                <Text style={{ fontSize: 13 }}>公司简介</Text>
              </div>
              <TextArea
                value={companyDesc}
                onChange={(e) => setCompanyDesc(e.target.value)}
                placeholder="请输入公司简介"
                rows={3}
                showCount
                maxLength={200}
              />
            </div>
            <div className="settings-field">
              <div className="settings-field-label">
                <GlobalOutlined style={{ color: '#722ed1' }} />
                <Text style={{ fontSize: 13 }}>公司官网</Text>
              </div>
              <Input
                value={companyWebsite}
                onChange={(e) => setCompanyWebsite(e.target.value)}
                placeholder="https://"
                prefix={<GlobalOutlined style={{ color: '#bfbfbf' }} />}
              />
            </div>
          </div>
        </div>

        {/* 偏好设置 */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="settings-card-icon settings-card-icon--prefs">
              <BulbOutlined />
            </div>
            <div>
              <Text strong style={{ fontSize: 16 }}>偏好设置</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>自定义您的使用体验</Text>
            </div>
          </div>
          <div className="settings-card-body">
            <div className="settings-switch-row">
              <div className="settings-switch-info">
                <BulbOutlined style={{ fontSize: 18, color: '#faad14' }} />
                <div>
                  <Text style={{ fontSize: 14 }}>深色模式</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>切换暗色主题以减轻眼睛疲劳</Text>
                </div>
              </div>
              <Switch checked={isDark} onChange={onToggleTheme} />
            </div>
            <div className="settings-switch-row">
              <div className="settings-switch-info">
                <BellOutlined style={{ fontSize: 18, color: '#52c41a' }} />
                <div>
                  <Text style={{ fontSize: 14 }}>任务完成通知</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>Agent 任务完成后推送通知</Text>
                </div>
              </div>
              <Switch checked={notifyTask} onChange={setNotifyTask} />
            </div>
            <div className="settings-switch-row">
              <div className="settings-switch-info">
                <BellOutlined style={{ fontSize: 18, color: '#ff4d4f' }} />
                <div>
                  <Text style={{ fontSize: 14 }}>异常告警通知</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>系统或 Agent 发生异常时告警</Text>
                </div>
              </div>
              <Switch checked={notifyError} onChange={setNotifyError} />
            </div>
          </div>
        </div>
      </div>
    </Drawer>
  );
}
