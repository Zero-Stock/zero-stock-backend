# Google Cloud Platform (GCP) 免费层部署指南

这份文档将指导你如何使用 Google Cloud 的**免费额度 (Free Tier)** 来部署当前的 Django 后端项目。针对学生和个人开发者，这是一个非常经济实惠（甚至是完全免费）的方案。

---

## 第一部分：申请 GCP 免费机器

Google Cloud 为每个账单账户提供了一个**永久免费**的 Compute Engine (VM) 实例额度。

### 1. 免费资源规格及学生额度最优解
如果你有 GitHub Student Developer Pack 或通过学校邮箱申请了 GCP 的教育额度（通常有 $50 - $300 的免费赠金），你可以选用性能更好的机器，而不是局限于永久免费的极低配置。

**方案 A：不消耗赠金（永久免费层 - 性能最低，适合测试）**
*   **实例类型**: `e2-micro` (2个 vCPU, **仅 1 GB 内存**)
*   **支持的区域 (Region) - 非常重要**:
    *   Oregon: `us-west1`
    *   Iowa: `us-central1`
    *   South Carolina: `us-east1`
    *(注意：必须且只能选择这三个区域之一，选择其他区域将产生费用！)*

**方案 B：消耗学生赠金的最优规格（推荐 - 性能好，足够跑前后端项目）**
*   **实例类型**: `e2-medium` (2个 vCPU, **4 GB 内存**) 或 `e2-standard-2` (2个 vCPU, **8 GB 内存**)。
    *(注：Django + Gunicorn 在 1GB 内存下容易遇到 OOM(Out of Memory) 导致服务中断，4GB 内存（`e2-medium`，按月约 $25）配合学生赠金可以无压力运行数月到一年。)*
*   **区域**: 如果选择计费机型，你可以选择离你最近的区域（例如你的目标用户在哪就选哪）。
*   **磁盘**: 30-50 GB standard persistent disk

> ⚠️ **重要提示 (防止超支)**: 无论选择何种方案，强烈建议在 GCP 后台的 **Billing (结算)** -> **Budgets & alerts (预算和警报)** 中设置一个每月预算（如 $10）。当花费达到预算的 50%, 90% 时会给你发邮件提醒，防止因为赠金用完而导致信用卡意外扣费。
    *(注意：必须且只能选择这三个区域之一，选择其他区域将产生费用！)*
*   **磁盘**: 30 GB standard persistent disk (标准持久化磁盘)
*   **网络带宽**: 每月 1 GB 的免费出站流量到北美以外的地区 (到北美境内一般免费额度更高)。

### 2. 创建 VM 实例流程
1. 访问 [Google Cloud Console](https://console.cloud.google.com/) 并注册/登录账号。如果提示绑定信用卡，这是为了验证身份，只要在免费额度内，不会扣费。
2. 在左侧导航栏选择 **Compute Engine -> VM 实例 (VM instances)**。
3. 点击 **创建实例 (Create Instance)**：
    *   **名称**: 自定义，例如 `canteen-backend`
    *   **区域**: 必须选择 `us-central1` (Iowa), `us-east1` (South Carolina), 或 `us-west1` (Oregon)。
    *   **机器配置 (Machine configuration)**:
        *   系列: `E2`
        *   机器类型: 
            *   如果你要**永久免费**: 选择 `e2-micro` (观察右侧页面的价格预估，如果符合免费计划，会显示部分免除提示)
            *   如果你要**消耗学生赠金享受高性能**: 选择 `e2-medium` (4GB内存) 或 `e2-standard-2` (8GB内存)。
    *   **启动磁盘 (Boot disk)**:
        *   操作系统: **Ubuntu**
        *   版本: **Ubuntu 22.04 LTS** (或 24.04 LTS)
        *   大小: 可以修改为 **30 GB**，磁盘类型选择 **标准永久性磁盘 (Standard persistent disk)** (默认的平衡磁盘或 SSD 不在免费范围内)。
    *   **防火墙 (Firewall)**:
        *   勾选 **允许 HTTP 流量 (Allow HTTP traffic)**。
        *   勾选 **允许 HTTPS 流量 (Allow HTTPS traffic)**。
4. 点击 **创建 (Create)** 等待机器启动。
5. 记录下分配给该虚拟机的 **外部 IP (External IP)**。

---

## 第二部分：服务器环境配置

机器创建好之后，点击实例列表右侧的 **SSH** 按钮，可以直接在浏览器中打开命令行终端。

### 1. 更新系统并安装系统依赖
在 SSH 终端中顺序执行以下命令：
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv git nginx -y
```

### 2. 克隆项目代码
将代码拉取到服务器上，这里假设我们拉取到 `~` (用户根目录)：
```bash
# 生成 SSH key（如果你的 Git 仓库是私有的）
ssh-keygen -t rsa -b 4096
cat ~/.ssh/id_rsa.pub # 复制这个公钥并添加到你的 Git 平台 (如 GitHub, GitLab 等) 的 SSH keys 中

# 克隆代码
git clone <你的项目 Git 仓库地址>
cd canteen-system  # 或者是你仓库名字，假设为 651 的话就 cd 651
```

### 3. 配置 Python 虚拟环境
```bash
python3 -m venv .venv
source .venv/bin/activate

# 安装项目依赖 (包含了 Django, DRF, gunicorn 等)
pip install -r requirements.txt
```

---

## 第三部分：配置 Django 项目

为了在生产环境中安全运行，我们需要修改 `canteen_system/settings.py`。
你可以使用 `nano canteen_system/settings.py` 或者 `vim` 来编辑。

### 1. 修改 settings.py
找到以下几项并进行修改：
```python
import os

# 1. 关闭 DEBUG 模式 (安全第一)
DEBUG = False

# 2. 允许的主机。将你的 VM 的【外部 IP地址】填进来，或者允许所有 '*' (不推荐)
ALLOWED_HOSTS = ['你的VM外部IP地址', 'localhost', '127.0.0.1']

# 3. 静态文件配置 (给 Nginx 使用)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
```

### 2. 生成静态文件与数据库迁移
确保在虚拟环境中执行 (`source .venv/bin/activate`)：
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

*(注意：目前项目使用的是 SQLite。对于免费服务器这种单机部署，SQLite 足够使用，数据库文件 `db.sqlite3` 直接存在项目目录下。如果你后续更新代码，请小心不要覆盖掉生产环境的 `db.sqlite3`)*

---

## 第四部分：配置 Gunicorn 和 Nginx

由于 Django 自带的 `manage.py runserver` 不适合生产环境，我们需要用 Gunicorn 作为应用服务器，Nginx 作为反向代理并代理静态文件。

### 1. 配置 Gunicorn 后台服务
我们需要创建一个 systemd 服务让 Gunicorn 在后台持续运行，并且开机自启。

```bash
sudo nano /etc/systemd/system/canteen.service
```
将会打开一个空文本，将以下内容粘贴进去（注意替换 `<你的用户名>` 和 `/path/to/project` 为实际路径，例如 `/home/your_username/651`）：

```ini
[Unit]
Description=gunicorn daemon for canteen system
After=network.target

[Service]
User=<你的用户名>
Group=www-data
WorkingDirectory=/home/<你的用户名>/<你的项目文件夹名>
ExecStart=/home/<你的用户名>/<你的项目文件夹名>/.venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/home/<你的用户名>/<你的项目文件夹名>/canteen.sock \
          canteen_system.wsgi:application

[Install]
WantedBy=multi-user.target
```
保存并退出 (nano: `Ctrl+O`, `Enter`, `Ctrl+X`)。

启动并启用该服务：
```bash
sudo systemctl start canteen
sudo systemctl enable canteen
sudo systemctl status canteen # 查看状态，确保是 active (running)
```

### 2. 配置 Nginx
创建一个新的 Nginx 站点配置文件：
```bash
sudo nano /etc/nginx/sites-available/canteen
```
粘贴以下内容：
```nginx
server {
    listen 80;
    server_name 你的VM外部IP地址;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    # 指向你的静态文件目录
    location /static/ {
        root /home/<你的用户名>/<你的项目文件夹名>;
    }

    # 代理传递给 Gunicorn socket
    location / {
        include proxy_params;
        proxy_pass http://unix:/home/<你的用户名>/<你的项目文件夹名>/canteen.sock;
    }
}
```
保存并退出。

激活配置并重启 Nginx：
```bash
sudo ln -s /etc/nginx/sites-available/canteen /etc/nginx/sites-enabled/
# 测试 Nginx 配置语法是否正确
sudo nginx -t
# 重启 Nginx
sudo systemctl restart nginx
```

---

## 第五部分：访问与后续更新

现在，你可以打开浏览器，直接访问你的 **VM 外部 IP 地址**。你应该能够看到后端的 API 或者能够被前端正常请求了。

### 常用运维命令
*   **查看应用运行日志**: `sudo journalctl -u canteen -f`
*   **查看 Nginx 错误日志**: `sudo tail -f /var/log/nginx/error.log`
*   **后续更新代码时**:
    ```bash
    cd <你的项目文件夹>
    git pull
    source .venv/bin/activate
    python manage.py migrate        # 如果有新的数据库修改
    python manage.py collectstatic  # 如果有新的静态文件
    sudo systemctl restart canteen  # 重启 Gunicorn 载入新代码
    ```
