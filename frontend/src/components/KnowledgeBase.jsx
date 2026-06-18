import { useState, useEffect } from 'react';
import {
  Drawer, Upload, List, Typography, Button, Tag, Empty, Popconfirm, message,
  Space, Tooltip, Progress, Alert,
} from 'antd';
import {
  FileTextOutlined,
  DeleteOutlined,
  InboxOutlined,
  LinkOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  fetchKnowledgeFiles,
  uploadKnowledgeFile,
  deleteKnowledgeFile,
  retryIndexFile,
} from '../api';

const { Dragger } = Upload;

const MAX_FILE_SIZE = 128 * 1024 * 1024;

const statusConfig = {
  indexed: { color: 'success', icon: <CheckCircleOutlined />, label: '已索引' },
  processing: { color: 'processing', icon: <LoadingOutlined />, label: '处理中' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, label: '失败' },
};

function formatFileSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(2) + ' MB';
  if (bytes >= 1e3) return (bytes / 1e3).toFixed(1) + ' KB';
  return bytes + ' B';
}

function formatDate(isoStr) {
  const d = new Date(isoStr);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export default function KnowledgeBase({ open, onClose }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  // 打开时加载数据
  useEffect(() => {
    if (open) {
      setLoading(true);
      fetchKnowledgeFiles()
        .then(setFiles)
        .catch((err) => message.error('加载知识库文件失败: ' + err.message))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const totalFiles = files.length;
  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  const indexedCount = files.filter((f) => f.status === 'indexed').length;

  const handleDelete = async (id) => {
    try {
      await deleteKnowledgeFile(id);
      setFiles((prev) => prev.filter((f) => f.id !== id));
      message.success('文件已从知识库中移除');
    } catch (err) {
      message.error('删除失败: ' + err.message);
    }
  };

  const handleRetry = async (id) => {
    try {
      setFiles((prev) =>
        prev.map((f) => (f.id === id ? { ...f, status: 'processing', chunks: 0 } : f))
      );
      message.info('正在重新索引文件...');
      const updated = await retryIndexFile(id);
      setFiles((prev) =>
        prev.map((f) => (f.id === id ? updated : f))
      );
      message.success('文件索引成功');
    } catch (err) {
      setFiles((prev) =>
        prev.map((f) => (f.id === id ? { ...f, status: 'failed' } : f))
      );
      message.error('索引失败: ' + err.message);
    }
  };

  const beforeUpload = async (file) => {
    // 前端验证
    if (!file.name.toLowerCase().endsWith('.txt')) {
      message.error('仅允许上传 .txt 文件！');
      return Upload.LIST_IGNORE;
    }
    if (file.size > MAX_FILE_SIZE) {
      message.error(
        `文件大小超过 128MB 限制！(当前 ${formatFileSize(file.size)})`
      );
      return Upload.LIST_IGNORE;
    }

    try {
      const newFile = await uploadKnowledgeFile(file);
      setFiles((prev) => [newFile, ...prev]);
      message.success(`"${file.name}" 上传成功`);

      // 等待索引完成 (mock 模式延迟 2.5s)
      setTimeout(async () => {
        try {
          const updated = await fetchKnowledgeFiles();
          setFiles(updated);
        } catch (e) { /* ignore */ }
      }, 3000);
    } catch (err) {
      message.error('上传失败: ' + err.message);
    }
    return false;
  };

  return (
    <Drawer
      title={
        <Space>
          <FileTextOutlined />
          <span>RAG 知识库</span>
        </Space>
      }
      open={open}
      onClose={onClose}
      width={480}
      extra={
        <Space size="middle">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            已索引 {indexedCount}/{totalFiles}
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {formatFileSize(totalSize)}
          </Typography.Text>
        </Space>
      }
      loading={loading}
    >
      <div className="rag-kb-container">
        {/* 上传区域 */}
        <div className="rag-upload-section">
          <Dragger
            name="file"
            multiple
            beforeUpload={beforeUpload}
            showUploadList={false}
            accept=".txt"
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽 .txt 文件上传</p>
            <p className="ant-upload-hint">
              仅支持 .txt 文件 &middot; 单文件最大 128MB
            </p>
          </Dragger>
        </div>

        <Alert
          message="每次上传限制 128MB，仅接受纯文本 (.txt) 文件"
          type="info"
          showIcon
          style={{ marginBottom: 16, fontSize: 12 }}
        />

        {/* 文件列表 */}
        <div className="rag-file-list">
          <Typography.Text strong style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
            已上传文件 ({files.length})
          </Typography.Text>

          {files.length > 0 ? (
            <List
              dataSource={files}
              renderItem={(file) => {
                const status = statusConfig[file.status] || statusConfig.failed;
                const progressPercent =
                  file.status === 'processing'
                    ? Math.floor(Math.random() * 60) + 20
                    : file.status === 'indexed'
                      ? 100
                      : 0;

                return (
                  <List.Item
                    className="rag-file-item"
                    actions={[
                      file.status === 'failed' && (
                        <Tooltip title="重新索引" key="retry">
                          <Button
                            type="text"
                            icon={<ReloadOutlined />}
                            size="small"
                            onClick={() => handleRetry(file.id)}
                          />
                        </Tooltip>
                      ),
                      <Popconfirm
                        key="delete"
                        title="确认删除此文件？"
                        description="将从知识库中移除该文件"
                        onConfirm={() => handleDelete(file.id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          size="small"
                        />
                      </Popconfirm>,
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      avatar={
                        <FileTextOutlined
                          style={{ fontSize: 22, color: '#1677ff' }}
                        />
                      }
                      title={
                        <Space size={8}>
                          <Typography.Text
                            strong
                            style={{ fontSize: 13, maxWidth: 200 }}
                            ellipsis
                          >
                            {file.name}
                          </Typography.Text>
                          <Tag
                            color={status.color}
                            icon={status.icon}
                            style={{ fontSize: 11 }}
                          >
                            {status.label}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div>
                          <Space size={12} wrap>
                            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                              {formatFileSize(file.size)}
                            </Typography.Text>
                            {file.chunks > 0 && (
                              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                                {file.chunks} 块
                              </Typography.Text>
                            )}
                            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                              {formatDate(file.uploadDate)}
                            </Typography.Text>
                          </Space>
                          <div style={{ marginTop: 4 }}>
                            <Tooltip title={file.fakeUrl}>
                              <Typography.Text
                                type="secondary"
                                style={{ fontSize: 10 }}
                                copyable={{ text: file.fakeUrl }}
                                ellipsis
                              >
                                <LinkOutlined style={{ marginRight: 4 }} />
                                {file.fakeUrl}
                              </Typography.Text>
                            </Tooltip>
                          </div>
                          {file.status === 'processing' && (
                            <Progress
                              percent={progressPercent}
                              size="small"
                              status="active"
                              style={{ marginTop: 4, marginBottom: 0 }}
                              strokeColor="#1677ff"
                            />
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                );
              }}
              style={{ maxHeight: 420, overflowY: 'auto' }}
            />
          ) : (
            <Empty
              description="暂无上传文件"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ marginTop: 40 }}
            />
          )}
        </div>
      </div>
    </Drawer>
  );
}
