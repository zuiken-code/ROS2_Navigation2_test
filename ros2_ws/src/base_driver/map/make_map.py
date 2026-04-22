# make_map.py
from PIL import Image, ImageDraw

# キャンバスサイズ（200x200 = 10m×10m）
WIDTH, HEIGHT = 200, 200
img = Image.new('L', (WIDTH, HEIGHT), 254)  # 254=通行可能（白）
draw = ImageDraw.Draw(img)

# ── 障害物を描く（色: 0=黒=障害物）────────────────
# 長方形: draw.rectangle([左上x, 左上y, 右下x, 右下y], fill=0)
# 座標は「ピクセル」で指定（1ピクセル=5cm）

# 壁（外周）
draw.rectangle([0, 0, 199, 5],   fill=0)  # 上壁
draw.rectangle([0, 194, 199, 199], fill=0)  # 下壁
draw.rectangle([0, 0, 5, 199],   fill=0)  # 左壁
draw.rectangle([194, 0, 199, 199], fill=0)  # 右壁

# 障害物① 中央の箱（50cm×50cm = 10px×10px）
# ロボット原点(0,0)は画像の中央(100,100)なので注意
# 実世界(x=1m, y=0m) → ピクセル(120, 100)
draw.rectangle([110, 90, 130, 110], fill=0)

# 障害物② 縦長の柱
draw.rectangle([60, 70, 70, 130], fill=0)

# 障害物③ 横長の壁
draw.rectangle([140, 130, 180, 140], fill=0)

img.save('/home/zuiken/Documents/ROS2_Navigation2_test/ros2_ws/src/base_driver/map/my_map1.pgm')
print('保存完了！')