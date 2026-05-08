import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

dayjs.locale('zh-cn');

import App from './App';
import './styles/theme.css';
import './styles/global.css';

/**
 * 通过 ConfigProvider.theme.token 把新中式色彩注入 AntD 设计令牌；
 * 细节再通过 theme.css 进一步覆盖（卡片/菜单/表格 hover 等）。
 */
const antdTheme = {
  token: {
    colorPrimary:        '#5E8B7E', // 水墨青
    colorInfo:           '#B58A3F', // 灰金
    colorSuccess:        '#4F8A6F',
    colorWarning:        '#B58A3F',
    colorError:          '#9B3A2E',

    colorTextBase:       '#1B262C',
    colorBgBase:         '#EEF1ED',
    colorBgContainer:    '#F8FAF7',
    colorBgLayout:       '#EEF1ED',
    colorBorder:         'rgba(94, 139, 126, 0.25)',
    colorBorderSecondary:'rgba(31, 42, 45, 0.08)',

    borderRadius:        12,
    borderRadiusLG:      16,
    borderRadiusSM:      8,

    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', " +
      "'Helvetica Neue', Helvetica, Arial, sans-serif",
    fontSize:            14,
    controlHeight:       36,
    boxShadow:           '0 8px 24px rgba(31, 42, 45, 0.07)',
    boxShadowSecondary:  '0 2px 8px rgba(31, 42, 45, 0.04)',
  },
  components: {
    Layout: {
      headerBg:   'transparent',
      siderBg:    '#1F2A2D',
      bodyBg:     '#EEF1ED',
    },
    Menu: {
      darkItemBg:           '#1F2A2D',
      darkSubMenuItemBg:    '#1F2A2D',
      darkItemSelectedBg:   '#5E8B7E',
      darkItemHoverBg:      'rgba(94, 139, 126, 0.18)',
      darkItemColor:        '#C7D6D2',
      darkItemSelectedColor:'#FFFFFF',
    },
    Button: {
      primaryShadow: 'none',
      defaultBorderColor: '#B58A3F',
      defaultColor: '#B58A3F',
    },
    Card: {
      headerBg: 'transparent',
      borderRadiusLG: 16,
    },
    Table: {
      headerBg: 'rgba(94, 139, 126, 0.10)',
      headerColor: '#1B262C',
      rowHoverBg: 'rgba(183, 207, 196, 0.30)',
    },
  },
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={antdTheme}>
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);
