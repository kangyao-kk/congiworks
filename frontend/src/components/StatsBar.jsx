import { Card, Row, Col, Statistic, Badge } from 'antd';

export default function StatsBar({ stats }) {
  return (
    <Card className="stats-bar" size="small">
      <Row gutter={[8, 0]} justify="space-around">
        <Col>
          <Statistic title="总计" value={stats.total} valueStyle={{ fontSize: 20 }} />
        </Col>
        <Col>
          <Statistic
            title="在线"
            value={stats.online}
            valueStyle={{ color: '#52c41a', fontSize: 20 }}
            prefix={<Badge status="success" />}
          />
        </Col>
        <Col>
          <Statistic
            title="离线"
            value={stats.offline}
            valueStyle={{ color: '#8c8c8c', fontSize: 20 }}
            prefix={<Badge status="default" />}
          />
        </Col>
      </Row>
    </Card>
  );
}
