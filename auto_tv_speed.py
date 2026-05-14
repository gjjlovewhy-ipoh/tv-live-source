name: 自动直播源测速更新
on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 6 * * *'

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: 拉取代码
        uses: actions/checkout@v5

      - name: 安装Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: 运行测速脚本
        run: python auto_tv_speed.py

      - name: 提交更新文件
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "actions@github.com"
          git add .
          git commit -m "自动生成直播网页" || echo "无变更无需提交"
          git push
