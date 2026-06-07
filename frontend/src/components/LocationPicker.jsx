import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Form, Input, InputNumber, Space, Typography } from 'antd';
import L from 'leaflet';
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = [35.8617, 104.1954];

function toNumber(value) {
  if (value === undefined || value === null || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function roundCoord(value) {
  return Number(Number(value).toFixed(6));
}

function MapClickHandler({ onPick }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function Recenter({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      const zoom = Math.max(map.getZoom(), 13);
      map.setView(position, zoom, { animate: true });
    }
  }, [map, position?.[0], position?.[1]]);
  return null;
}

export default function LocationPicker({
  form,
  latitudeName = 'latitude',
  longitudeName = 'longitude',
  noteName = 'location_note',
  title = '现场位置记录',
  description = '点击地图、拖动标记，或手动输入经纬度，用于记录现场位置。',
  notePlaceholder = '可记录公开可描述的位置、周边环境或资料来源',
  disabled = false,
}) {
  const latitude = Form.useWatch(latitudeName, form);
  const longitude = Form.useWatch(longitudeName, form);
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState('');

  const lat = toNumber(latitude);
  const lng = toNumber(longitude);
  const position = useMemo(() => (
    lat !== null && lng !== null ? [lat, lng] : null
  ), [lat, lng]);

  function setPosition(nextLat, nextLng) {
    form.setFieldsValue({
      [latitudeName]: roundCoord(nextLat),
      [longitudeName]: roundCoord(nextLng),
    });
    setGeoError('');
  }

  function useBrowserLocation() {
    if (!navigator.geolocation) {
      setGeoError('当前浏览器不支持定位，请手动输入经纬度或在地图上选点。');
      return;
    }
    setLocating(true);
    setGeoError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition(pos.coords.latitude, pos.coords.longitude);
        setLocating(false);
      },
      (err) => {
        setGeoError(err?.message || '浏览器定位失败，请确认权限或手动选点。');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  }

  function clearLocation() {
    form.setFieldsValue({
      [latitudeName]: undefined,
      [longitudeName]: undefined,
    });
    setGeoError('');
  }

  return (
    <div style={{ width: '100%' }}>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <div>
          <Typography.Text strong>{title}</Typography.Text>
          <div style={{ color: 'var(--ml-text-muted)', marginTop: 4 }}>{description}</div>
        </div>

        <div
          style={{
            height: 280,
            width: '100%',
            overflow: 'hidden',
            border: '1px solid var(--ml-border)',
            borderRadius: 8,
            background: '#eef1ed',
          }}
        >
          <MapContainer
            center={position || DEFAULT_CENTER}
            zoom={position ? 13 : 4}
            scrollWheelZoom
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {!disabled && <MapClickHandler onPick={setPosition} />}
            {position && (
              <>
                <Recenter position={position} />
                <Marker
                  position={position}
                  draggable={!disabled}
                  eventHandlers={{
                    dragend(event) {
                      const next = event.target.getLatLng();
                      setPosition(next.lat, next.lng);
                    },
                  }}
                />
              </>
            )}
          </MapContainer>
        </div>

        <Space wrap size={12} align="start">
          <Form.Item name={latitudeName} label="纬度" style={{ width: 170 }}>
            <InputNumber
              min={-90}
              max={90}
              precision={6}
              style={{ width: '100%' }}
              placeholder="例如 31.2304"
              disabled={disabled}
            />
          </Form.Item>
          <Form.Item name={longitudeName} label="经度" style={{ width: 170 }}>
            <InputNumber
              min={-180}
              max={180}
              precision={6}
              style={{ width: '100%' }}
              placeholder="例如 121.4737"
              disabled={disabled}
            />
          </Form.Item>
          <Form.Item label="定位操作" style={{ width: 240 }}>
            <Space>
              <Button loading={locating} onClick={useBrowserLocation} disabled={disabled}>
                当前位置
              </Button>
              <Button onClick={clearLocation} disabled={disabled || !position}>
                清除
              </Button>
            </Space>
          </Form.Item>
        </Space>

        <Form.Item name={noteName} label="地点备注">
          <Input.TextArea rows={2} placeholder={notePlaceholder} disabled={disabled} />
        </Form.Item>

        {position ? (
          <Alert
            type="success"
            showIcon
            message={`已记录现场坐标：${position[0].toFixed(6)}, ${position[1].toFixed(6)}`}
          />
        ) : (
          <Alert type="info" showIcon message="未选择位置时也可以保存记录；地图选点仅用于现场资料归档。" />
        )}
        {geoError && <Alert type="warning" showIcon message={geoError} />}
      </Space>
    </div>
  );
}
