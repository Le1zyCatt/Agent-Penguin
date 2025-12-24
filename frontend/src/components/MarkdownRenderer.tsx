import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <div className="markdown-content" style={{ lineHeight: 1.6 }}>
      <ReactMarkdown
        children={content}
        remarkPlugins={[remarkGfm]} // 启用 GitHub Flavored Markdown，支持表格、删除线等
        components={{
          // 自定义渲染组件以匹配现有样式
          p: ({ node, ...props }) => <p style={{ margin: '8px 0', whiteSpace: 'pre-wrap' }} {...props} />,
          h1: ({ node, ...props }) => <h1 style={{ fontSize: '1.5em', margin: '12px 0' }} {...props} />,
          h2: ({ node, ...props }) => <h2 style={{ fontSize: '1.4em', margin: '10px 0' }} {...props} />,
          h3: ({ node, ...props }) => <h3 style={{ fontSize: '1.3em', margin: '8px 0' }} {...props} />,
          ul: ({ node, ...props }) => <ul style={{ margin: '8px 0', paddingLeft: '20px' }} {...props} />,
          ol: ({ node, ...props }) => <ol style={{ margin: '8px 0', paddingLeft: '20px' }} {...props} />,
          li: ({ node, ...props }) => <li style={{ margin: '4px 0' }} {...props} />,
          code: ({ node, ...props }) => (
            <code
              style={{
                backgroundColor: '#f4f4f4',
                padding: '2px 4px',
                borderRadius: '3px',
                fontFamily: 'monospace'
              }}
              {...props}
            />
          ),
          pre: ({ node, ...props }) => (
            <pre
              style={{
                backgroundColor: '#f4f4f4',
                padding: '8px',
                borderRadius: '4px',
                overflow: 'auto',
                fontFamily: 'monospace'
              }}
              {...props}
            />
          ),
          strong: ({ node, ...props }) => <strong style={{ fontWeight: 600 }} {...props} />,
          em: ({ node, ...props }) => <em style={{ fontStyle: 'italic' }} {...props} />,
          // 表格支持
          table: ({ node, ...props }) => (
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                margin: '8px 0',
                fontSize: '0.9em'
              }}
              {...props}
            />
          ),
          thead: ({ node, ...props }) => <thead style={{ backgroundColor: '#f8f9fa' }} {...props} />,
          tbody: ({ node, ...props }) => <tbody {...props} />,
          tr: ({ node, ...props }) => <tr style={{ borderBottom: '1px solid #ddd' }} {...props} />,
          th: ({ node, ...props }) => (
            <th
              style={{
                padding: '8px',
                textAlign: 'left',
                fontWeight: 600,
                backgroundColor: '#f8f9fa',
                border: '1px solid #ddd'
              }}
              {...props}
            />
          ),
          td: ({ node, ...props }) => (
            <td
              style={{
                padding: '8px',
                textAlign: 'left',
                border: '1px solid #ddd'
              }}
              {...props}
            />
          ),
        }}
      />
    </div>
  );
};

export default MarkdownRenderer;
