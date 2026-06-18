import { Card, Descriptions, Tag, Typography, Row, Col, Statistic, Timeline, Empty, Divider, Button, Tooltip } from 'antd';
import { SendOutlined, ClockCircleOutlined } from '@ant-design/icons';

const activityColorMap = {
  agent_started: 'green',
  agent_stopped: 'orange',
  task_received: 'blue',
  thinking_started: 'purple',
  task_completed: 'cyan',
  config_updated: 'gold',
  error_occurred: 'red',
};

function formatTimestamp(isoStr) {
  const date = new Date(isoStr);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const mins = String(date.getMinutes()).padStart(2, '0');
  const secs = String(date.getSeconds()).padStart(2, '0');
  return `${month}-${day} ${hours}:${mins}:${secs}`;
}

function formatTokens(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  return n.toLocaleString();
}

export default function AgentDetail({ agent, activityLogs, onSendPreset }) {
  if (!agent) {
    return (
      <div className="agent-detail" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="选择一个 Agent 查看详情" />
      </div>
    );
  }

  return (
    <div className="agent-detail">
      {/* 预设任务 */}
      <Card title="预设任务" size="small" className="detail-section">
        {agent.presetTasks && agent.presetTasks.length > 0 ? (
          <div className="preset-tasks-list">
            {agent.presetTasks.map((task, idx) => (
              <Tooltip key={idx} title={task.prompt}>
                <Button
                  size="small"
                  icon={<SendOutlined />}
                  onClick={() => onSendPreset && onSendPreset(task.prompt)}
                  disabled={agent.status !== 'online'}
                  block
                  style={{ textAlign: 'left', marginBottom: 6 }}
                >
                  <span className="preset-task-label">{task.label}</span>
                </Button>
              </Tooltip>
            ))}
          </div>
        ) : (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>暂无预设任务</Typography.Text>
        )}
      </Card>

      <Divider style={{ margin: '12px 0' }} />

      {/* 配置信息 */}
      <Card title="配置信息" size="small" className="detail-section">
        <Descriptions column={1} size="small" colon={false}>
          <Descriptions.Item label="模型">{agent.model}</Descriptions.Item>
          <Descriptions.Item label="温度">{agent.temperature}</Descriptions.Item>
          <Descriptions.Item label="最大 Token">{agent.maxTokens.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="分类">
            <Tag>{agent.category}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Divider style={{ margin: '12px 0' }} />

      {/* 系统提示词 */}
      <Card title="系统提示词" size="small" className="detail-section">
        <Typography.Paragraph
          ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
          style={{ fontSize: 12, color: '#666', margin: 0 }}
        >
          {agent.systemPrompt}
        </Typography.Paragraph>
      </Card>

      <Divider style={{ margin: '12px 0' }} />

      {/* 性能指标 */}
      <Card title="性能指标" size="small" className="detail-section">
        <Row gutter={[12, 12]}>
          <Col span={12}>
            <Statistic
              title="对话数"
              value={agent.metrics.totalConversations}
              formatter={(v) => v.toLocaleString()}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="平均响应"
              value={agent.metrics.avgResponseTime}
              suffix="秒"
              precision={1}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="成功率"
              value={agent.metrics.successRate * 100}
              suffix="%"
              precision={1}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="Token 用量"
              value={agent.metrics.tokensUsed}
              formatter={formatTokens}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
        </Row>
      </Card>

      <Divider style={{ margin: '12px 0' }} />

      {/* 任务时间轴 */}
      <Card
        title={
          <span>
            <ClockCircleOutlined style={{ marginRight: 6 }} />
            任务时间轴
          </span>
        }
        size="small"
        className="detail-section"
      >
        {(activityLogs || []).length > 0 ? (
          <Timeline
            items={(activityLogs || []).slice(0, 20).map((log) => ({
              color: activityColorMap[log.type] || 'gray',
              children: (
                <div>
                  <Typography.Text style={{ fontSize: 11 }} type="secondary">
                    {formatTimestamp(log.timestamp)}
                  </Typography.Text>
                  <br />
                  <Typography.Text style={{ fontSize: 12 }}>
                    {log.description}
                  </Typography.Text>
                </div>
              ),
            }))}
          />
        ) : (
          <Empty description="暂无任务记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  );
}
