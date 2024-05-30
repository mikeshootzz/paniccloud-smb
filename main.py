from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

SAMBA_CONF_PATH = '/etc/samba/smb.conf'
MOUNT_DIR = '/mnt'


def add_samba_share(share_name, path, read_only, username):
    with open(SAMBA_CONF_PATH, 'a') as smb_conf:
        smb_conf.write(f"\n[{share_name}]\n")
        smb_conf.write(f"path = {path}\n")
        smb_conf.write(f"read only = {'yes' if read_only else 'no'}\n")
        smb_conf.write(f"browsable = yes\n")
        smb_conf.write(f"valid users = {username}\n")


def add_user(username, password, read_only):
    # Create system user
    subprocess.run(['sudo', 'useradd', '-M', '-s', '/sbin/nologin', username])
    subprocess.run(['echo', f'{username}:{password}', '|', 'sudo', 'chpasswd'])
    subprocess.run(['sudo', 'smbpasswd', '-a', username], input=f'{password}\n{password}\n', text=True)

    # Set permissions on the directory
    user_home_dir = os.path.join(MOUNT_DIR, username)
    os.makedirs(user_home_dir, exist_ok=True)
    subprocess.run(['sudo', 'chown', f'{username}:{username}', user_home_dir])
    subprocess.run(['sudo', 'chmod', '700' if read_only else '770', user_home_dir])

    return user_home_dir


@app.route('/create_share', methods=['POST'])
def create_share():
    data = request.json
    share_name = data.get('share_name')
    username = data.get('username')
    password = data.get('password')
    access = data.get('access')  # "read" or "readwrite"

    if not share_name or not username or not password or access not in ["read", "readwrite"]:
        return jsonify({"error": "Invalid input"}), 400

    read_only = access == "read"
    user_home_dir = add_user(username, password, read_only)
    add_samba_share(share_name, user_home_dir, read_only, username)

    subprocess.run(['sudo', 'systemctl', 'restart', 'smbd'])

    return jsonify({"message": "SMB share created successfully"}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
