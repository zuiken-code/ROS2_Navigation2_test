# 🤖 ROS2 Navigation2 テスト

Raspberry Pi 5 と安価な 2WD ロボットシャーシを使った、ROS 2 (Jazzy) + Navigation2 による自律移動ロボットのテストプロジェクトです。

LiDAR などの高価なセンサーを使わず、**ホイールエンコーダー（フォトインタラプタ）のみ**でオドメトリを取得し、Nav2 による経路計画・自律走行を実現しています。

## 🎬 デモ

### ソフトウェアのみの実験
<a href="https://x.com/ZuikenCode/status/2047079262629577128?s=20">
  <img src="https://img.shields.io/badge/𝕏-デモ動画①-black?style=for-the-badge&logo=x" alt="Demo 1" />
</a>



### 実際に動かしている様子
<a href="https://x.com/ZuikenCode/status/2051650061059469709?s=20">
  <img src="https://img.shields.io/badge/𝕏-デモ動画②-black?style=for-the-badge&logo=x" alt="Demo 2" />
</a>

## 📋 目次

- [ハードウェア構成](#-ハードウェア構成)
- [システム構成](#-システム構成)
- [ディレクトリ構成](#-ディレクトリ構成)
- [セットアップ](#-セットアップ)
- [使い方](#-使い方)
- [パラメータ](#-パラメータ)
- [TF ツリー](#-tf-ツリー)

## 🔧 ハードウェア構成

| パーツ | 製品名 | リンク |
|---|---|---|
| コンピュータ | Raspberry Pi 5 | — |
| シャーシ | 2WD Mini Smart Robot Mobile Platform Kit | [秋月電子](https://akizukidenshi.com/catalog/g/g113651/) |
| エンコーダー | IR 赤外線スロット付きフォトインタラプタセンサー | [Amazon](https://amzn.asia/d/00TZoSjK) |
| モータードライバー | 2ch DC モータードライブモジュール（ダブル H ブリッジ） | [Amazon](https://amzn.asia/d/0cKkInjR) |

### GPIO ピン配置

| 機能 | GPIO ピン |
|---|---|
| 右モーター Forward | GPIO 18 |
| 右モーター Backward | GPIO 17 |
| 左モーター Forward | GPIO 23 |
| 左モーター Backward | GPIO 22 |
| 右エンコーダー | GPIO 10 |
| 左エンコーダー | GPIO 2 |

## 🏗️ システム構成

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi 5                       │
│                                                         │
│  ┌──────────┐  cmd_vel  ┌──────────────┐               │
│  │ Nav2     │ ────────► │ base_driver  │──► モーター    │
│  │ Stack    │           └──────────────┘               │
│  │          │  odom     ┌──────────────┐               │
│  │          │ ◄──────── │ encoder_odom │◄── エンコーダー│
│  └──────────┘           └──────────────┘               │
│                                                         │
│  ┌──────────────────┐   ┌──────────────────┐           │
│  │ robot_state_pub  │   │ static_tf_pub    │           │
│  │ (URDF → TF)      │   │ (map → odom)     │           │
│  └──────────────────┘   └──────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### ノード一覧

| ノード | 説明 |
|---|---|
| `base_driver` | `cmd_vel` を受けてモーターを PWM 制御（0.5 秒タイムアウト付き） |
| `encoder_odom` | フォトインタラプタを 500Hz でポーリングし、オドメトリ + TF を 10Hz で配信 |
| `static_tf_pub` | `map` → `odom` の静的 TF を配信（AMCL の代替） |

## 📁 ディレクトリ構成

```
ROS2_Navigation2_test/
└── ros2_ws/
    └── src/
        └── base_driver/              # ROS 2 パッケージ
            ├── base_driver/
            │   ├── driver.py         # モーター制御ノード
            │   ├── encoder.py        # エンコーダーオドメトリノード
            │   └── static_tf_pub.py  # 静的 TF 配信ノード
            ├── config/
            │   └── nav2_params.yaml  # Nav2 パラメータ
            ├── launch/
            │   ├── base_driver.launch.py  # 基本起動（手動操縦用）
            │   └── bringup.launch.py      # Nav2 フル起動（自律走行用）
            ├── map/
            │   ├── make_map.py       # 地図生成スクリプト
            │   ├── my_map1.pgm       # 障害物付き地図
            │   ├── empty_map.pgm     # 空の地図
            │   └── empty_map.yaml    # 地図メタデータ
            ├── urdf/
            │   └── robot.urdf.xml    # ロボットモデル定義
            ├── package.xml
            ├── setup.py
            └── setup.cfg
```

## 🚀 セットアップ

### 前提条件

- Raspberry Pi 5
- ROS 2 Jazzy
- Navigation2

### 依存パッケージのインストール

```bash
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
                 ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher \
                 ros-jazzy-tf2-ros
```

### Python ライブラリ

```bash
pip install gpiozero lgpio Pillow
```

### ビルド

```bash
cd ros2_ws
colcon build --packages-select base_driver
source install/setup.bash
```

## 🎮 使い方

### 手動操縦（キーボード）

ターミナル 1:

```bash
ros2 launch base_driver base_driver.launch.py
```

ターミナル 2:

```bash
ros2 run turtlesim turtle_teleop_key
```

> **Note**: `base_driver.launch.py` では `cmd_vel` を `/turtle1/cmd_vel` にリマップしているため、`turtle_teleop_key` でそのまま操縦できます。

### Nav2 自律走行

```bash
ros2 launch base_driver bringup.launch.py
```

別端末で RViz2 を起動し、`2D Goal Pose` で目標地点を指定すると自律走行を開始します：

```bash
rviz2
```

### 地図のカスタマイズ

`map/make_map.py` を編集して障害物を追加・変更できます：

```bash
cd ros2_ws/src/base_driver/map
python3 make_map.py
```

## ⚙️ パラメータ

### ロボット物理パラメータ

| パラメータ | 値 | 説明 |
|---|---|---|
| `wheel_radius` | 0.030 m | 車輪半径 |
| `wheel_separation` | 0.10 m | 車輪間距離（トレッド） |
| `ticks_per_rev` | 40 | エンコーダーの 1 回転あたりのティック数 |
| `robot_radius` | 0.10 m | ロボットの衝突判定半径 |

### Nav2 主要パラメータ

| パラメータ | 値 |
|---|---|
| コントローラー | RegulatedPurePursuitController |
| プランナー | NavfnPlanner |
| 目標速度 | 0.15 m/s |
| ゴール許容誤差 (xy) | 0.20 m |
| ゴール許容誤差 (yaw) | 0.30 rad |

## 🌳 TF ツリー

```
map
 └── odom            (static_tf_pub: 静的)
      └── base_footprint  (encoder_odom: オドメトリ)
           └── base_link       (URDF: 固定)
                ├── left_wheel      (URDF: continuous)
                ├── right_wheel     (URDF: continuous)
                └── laser_frame     (URDF: 固定)
```

## 📝 設計メモ

- **AMCL を使わない理由**: LiDAR がないため、`map` → `odom` の変換は静的 TF で固定しています。これにより自己位置推定の精度は落ちますが、エンコーダーオドメトリのみで Nav2 の経路追従を試すことができます。
- **エンコーダーの方向推定**: エンコーダー自体は回転方向を検出できない（スロット式フォトインタラプタ）ため、`cmd_vel` の指令値から回転方向を推定しています。
- **タイムアウト安全機構**: `cmd_vel` が 0.5 秒以上届かない場合、モーターを自動停止します。

## 📄 ライセンス

MIT
