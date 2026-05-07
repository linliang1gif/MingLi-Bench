import React from 'react';
import { Layout, Menu } from 'antd';
import {
  MessageOutlined,
  UserOutlined,
  CompassOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import LogoSeal from '../components/LogoSeal';

const { Sider, Header, Content } = Layout;

/**
 * 明理 AI 主导航。
 */
const NAV = [
  { key: '/',          icon: <MessageOutlined />,  label: 'AI 问命' },
  { key: '/subjects',  icon: <UserOutlined />,     label: '命主档案' },
  { key: '/chart',     icon: <CompassOutlined />,  label: '命盘分析' },
  { key: '/reports',   icon: <FileTextOutlined />, label: '分析报告' },
  { key: '/history',   icon: <HistoryOutlined />,  label: '历史记录' },
  { key: '/settings',  icon: <SettingOutlined />,  label: '设置' },
];

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();

  // 选中匹配：精确匹配 + 子路径回落
  const selectedKey =
    NAV.map((n) => n.key)
       .filter((k) => k !== '/' && location.pathname.startsWith(k))
       .sort((a, b) => b.length - a.length)[0] ||
    (location.pathname === '/' ? '/' : '/');

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        className="ml-side"
        width={232}
        breakpoint="lg"
        style={{
          position: 'sticky',
          top: 0,
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Logo 区 */}
        <div
          style={{
            padding: '22px 18px 16px',
            borderBottom: '1px solid rgba(94, 139, 126, 0.20)',
            marginBottom: 6,
            flexShrink: 0,
          }}
        >
          <LogoSeal size={38} theme="dark" />
        </div>

        {/* 菜单可滚动区 */}
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          <Menu
            className="ml-side-menu"
            mode="inline"
            selectedKeys={[selectedKey]}
            items={NAV.map((n) => ({ key: n.key, icon: n.icon, label: n.label }))}
            onClick={({ key }) => navigate(key)}
          />
        </div>

        {/* 底部签名（正常流，不再遮拡菜单项） */}
        <div
          style={{
            flexShrink: 0,
            padding: '12px 0 14px',
            textAlign: 'center',
            color: 'rgba(199, 214, 210, 0.55)',
            fontSize: 12,
            letterSpacing: 2,
            fontFamily: 'var(--ml-font-serif)',
            borderTop: '1px solid rgba(94, 139, 126, 0.14)',
          }}
        >
          以题为尺 · 以盘为据
        </div>
      </Sider>

      <Layout>
        <Header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 5,
            backdropFilter: 'blur(6px)',
            background: 'rgba(238, 241, 237, 0.78)',
            borderBottom: '1px solid var(--ml-divider)',
            padding: '0 28px',
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div />
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ color: 'var(--ml-bronze)', fontSize: 12, letterSpacing: 1 }}>
              测试体验版
            </span>
          </div>
        </Header>

        <Content className="ml-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
