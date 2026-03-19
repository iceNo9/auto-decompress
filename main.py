import sys
import os
import argparse
import patoolib
from ruamel.yaml import YAML
import logging
from logging.handlers import TimedRotatingFileHandler

# 创建全局 logger 对象
logger = logging.getLogger("AutoDecompress")
logger.setLevel(logging.DEBUG)  # 全局日志等级

# 确保log目录存在
log_dir = "log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    "[%(levelname)s] %(filename)s:%(lineno)d: %(message)s"
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 按日轮转的文件处理器
log_file = os.path.join(log_dir, "auto_decompress.log")
file_handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",  # 每天午夜轮转
    interval=1,       # 间隔1天
    backupCount=30,   # 保留30天的日志文件
    encoding="utf-8",
    delay=False,      # 立即创建文件
    utc=False         # 使用本地时间
)

# 设置日志文件名格式（会在原文件名后添加日期）
# 例如：archive_inspector.log -> archive_inspector.log.2024-01-01
file_handler.suffix = "%Y-%m-%d"  # 设置日期格式

file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def load_passwords(yaml_file='passwd.yaml'):
    """加载密码列表，如果文件不存在则创建空白密码文件"""
    if not os.path.exists(yaml_file):
        logger.info(f"密码文件 {yaml_file} 不存在，创建空白密码文件")
        # 创建空白密码文件
        create_empty_password_file(yaml_file)
        return []
    
    yaml = YAML()
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.load(f) or {'passwd': []}

    passwords = data.get('passwd', [])
    return sorted([str(p) for p in passwords], key=lambda x: (x == '', x))

def create_empty_password_file(yaml_file='passwd.yaml'):
    """创建空白密码文件"""
    yaml = YAML()
    data = {'passwd': []}
    
    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.abspath(yaml_file)) if os.path.dirname(yaml_file) else '.', exist_ok=True)
    
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)
    logger.info(f"已创建空白密码文件: {yaml_file}")

def save_passwords(passwords, yaml_file='passwd.yaml'):
    """保存密码列表到YAML文件"""
    yaml = YAML()
    # 转换为列表并排序
    pwd_list = sorted(list(set([str(p) for p in passwords if p != ''])))  # 去重并排除空密码
    
    # 如果原来有空密码，可以加回来，但通常我们不保存空密码
    data = {'passwd': pwd_list}
    
    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.abspath(yaml_file)) if os.path.dirname(yaml_file) else '.', exist_ok=True)
    
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)
    logger.info(f"密码已保存到 {yaml_file}")

def add_password(password, yaml_file='passwd.yaml'):
    """添加密码到YAML文件"""
    passwords = load_passwords(yaml_file)
    if password in passwords:
        logger.info(f"密码 '{password}' 已存在")
    else:
        passwords.append(password)
        save_passwords(passwords, yaml_file)
        logger.info(f"密码 '{password}' 已添加")

def remove_password(password, yaml_file='passwd.yaml'):
    """从YAML文件中移除密码"""
    passwords = load_passwords(yaml_file)
    if password in passwords:
        passwords.remove(password)
        save_passwords(passwords, yaml_file)
        logger.info(f"密码 '{password}' 已移除")
    else:
        logger.info(f"密码 '{password}' 不存在")

def get_output_dir(archive_path, output_dir=None):
    """获取输出目录路径
    如果指定了output_dir，则在该目录下创建以文件名命名的子目录
    否则使用与输入文件同级，使用文件名作为目录名
    """
    file_name = os.path.splitext(os.path.basename(archive_path))[0]
    
    if output_dir:
        # 在指定的输出目录下创建以文件名命名的子目录
        return os.path.join(output_dir, file_name)
    else:
        # 使用原文件所在目录，创建以文件名命名的子目录
        base_dir = os.path.dirname(archive_path)
        return os.path.join(base_dir, file_name)

def ensure_archive_file(archive_path, force_zip=True):
    """确保文件路径指向一个归档文件，必要时添加.zip后缀"""
    # 如果文件存在且已经是归档文件，直接返回
    if os.path.isfile(archive_path) and patoolib.is_archive(archive_path):
        return archive_path
    
    # 文件存在但不是归档文件
    if os.path.isfile(archive_path) and not patoolib.is_archive(archive_path):
        logger.warning(f"文件 '{archive_path}' 存在但不是有效的归档文件")
        
        zip_path = archive_path + '.zip'
        
        if force_zip:
            # 自动重命名
            if os.path.exists(zip_path):
                logger.error(f"无法重命名，{zip_path} 已存在")
                return archive_path
            os.rename(archive_path, zip_path)
            logger.info(f"已自动重命名为: {zip_path}")
            
            # 检查重命名后的文件是否是归档文件
            if patoolib.is_archive(zip_path):
                return zip_path
            else:
                logger.error(f"重命名后的文件 '{zip_path}' 仍然不是有效的归档文件")
                return archive_path
        else:
            # 交互式询问
            response = input(f"文件 '{archive_path}' 存在但不是归档文件，是否重命名为 '{archive_path}.zip'? (y/n): ")
            if response.lower() == 'y':
                if os.path.exists(zip_path):
                    logger.error(f"无法重命名，{zip_path} 已存在")
                    return archive_path
                os.rename(archive_path, zip_path)
                logger.info(f"已重命名为: {zip_path}")
                
                # 检查重命名后的文件是否是归档文件
                if patoolib.is_archive(zip_path):
                    return zip_path
                else:
                    logger.error(f"重命名后的文件 '{zip_path}' 仍然不是有效的归档文件")
                    return archive_path
    
    # 文件不存在或无法处理
    return archive_path

def try_passwords(archive_path, passwords, output_dir=None, force_zip=True):
    """尝试密码列表解压"""
    # 确保文件路径是归档文件
    archive_path = ensure_archive_file(archive_path, force_zip)
    
    if not os.path.isfile(archive_path):
        logger.error(f"文件不存在: {archive_path}")
        return None
    
    if not patoolib.is_archive(archive_path):
        logger.error(f"文件不是支持的归档格式: {archive_path}")
        return None
    
    # 准备输出目录
    outdir = get_output_dir(archive_path, output_dir)
    os.makedirs(outdir, exist_ok=True)
    
    if output_dir:
        logger.info(f"解压到指定目录: {outdir}")
    else:
        logger.info(f"解压到默认目录: {outdir}")
    
    # 先尝试空密码
    all_passwords = [''] + passwords
    for pwd in all_passwords:
        pwd_display = pwd if pwd != '' else '空密码'
        logger.debug(f"尝试密码: {pwd_display}")
        try:
            # list_archive 会在密码错误时抛出 PatoolError
            patoolib.list_archive(archive_path, verbosity=0, program=None, interactive=False, password=pwd)

            if pwd == '':
                logger.debug(f"[成功] 文件无需密码")
            else:
                logger.debug(f"[成功] 找到可用密码: {pwd}")
            
            # 解压文件
            patoolib.extract_archive(archive_path, verbosity=1, outdir=outdir, program=None, interactive=False, password=pwd)
            logger.info(f"[完成] 文件已解压到: {outdir} 密码: {pwd_display}")
            return pwd
        except Exception as e:
            error_msg = str(e)
            # 常见的密码错误提示
            if "password" in error_msg.lower() or "wrong" in error_msg.lower():
                logger.info(f"[失败] 密码错误")
            else:
                logger.warning(f"[失败] 其他错误: {error_msg}")
            continue
    
    logger.error("所有密码尝试失败")
    return None

def main():
    parser = argparse.ArgumentParser(
        description='压缩文件密码破解工具（默认强制添加.zip后缀）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s /path/to/file                 # 尝试破解压缩文件（自动添加.zip后缀）
  %(prog)s /path/to/file.zip              # 尝试破解zip文件
  %(prog)s -a 123456                      # 添加密码123456到密码列表
  %(prog)s -d 123456                      # 从密码列表中移除123456
  %(prog)s -l                             # 列出当前所有密码
  %(prog)s /path/to/file -o /output/dir   # 解压到指定目录
  %(prog)s /path/to/file --no-force       # 不自动添加.zip后缀
        '''
    )
    
    parser.add_argument('target', nargs='?', help='压缩文件路径或操作目标')
    parser.add_argument('-a', '--add', metavar='密码', help='添加一个密码到密码列表')
    parser.add_argument('-d', '--remove', metavar='密码', help='从密码列表中移除一个密码')
    parser.add_argument('-l', '--list', action='store_true', help='列出当前所有密码')
    parser.add_argument('-o', '--output', metavar='目录', help='指定解压输出目录（将在该目录下创建以文件名命名的子目录）')
    parser.add_argument('--no-force', action='store_true', help='不自动添加.zip后缀（默认会自动添加）')
    parser.add_argument('-y', '--yes', action='store_true', help='自动确认所有提示（默认模式）')
    
    args = parser.parse_args()
    
    # 处理密码管理命令
    if args.add:
        add_password(args.add)
        return
    
    if args.remove:
        remove_password(args.remove)
        return
    
    if args.list:
        passwords = load_passwords()
        if passwords:
            logger.info("当前密码列表:")
            for i, pwd in enumerate(passwords, 1):
                logger.info(f"  {i}. {pwd}")
            logger.info(f"总计: {len(passwords)} 个密码")
        else:
            logger.info("密码列表为空")
        return
    
    # 如果没有target参数，显示帮助信息
    if not args.target:
        parser.print_help()
        return
    
    # 处理文件路径
    archive_path = args.target
    
    # 默认是强制模式，除非指定了--no-force
    force_mode = not args.no_force
    
    if not os.path.isfile(archive_path):
        logger.error(f"文件不存在 - {archive_path}")
        sys.exit(1)
    
    # 检查文件是否为归档文件
    if not patoolib.is_archive(archive_path):
        logger.warning(f"文件 '{archive_path}' 不是有效的归档文件")
        
        # 如果是强制模式，尝试添加.zip后缀
        if force_mode:
            zip_path = archive_path + '.zip'
            if not os.path.exists(zip_path):
                # 重命名文件
                os.rename(archive_path, zip_path)
                logger.info(f"自动添加.zip后缀，文件已重命名为: {zip_path}")
                archive_path = zip_path
                
                # 检查重命名后是否为归档文件
                if not patoolib.is_archive(archive_path):
                    logger.error(f"重命名后的文件 '{archive_path}' 仍然不是有效的归档文件")
                    sys.exit(1)
            else:
                logger.error(f"{zip_path} 已存在，无法自动重命名")
                sys.exit(1)
        else:
            logger.error(f"文件不是有效的归档文件，且未启用强制模式（--no-force）")
            sys.exit(1)
    
    # 如果指定了输出目录，检查并创建
    output_dir = None
    if args.output:
        output_dir = os.path.abspath(args.output)
        if not os.path.exists(output_dir):
            logger.info(f"输出目录不存在，将创建: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        elif not os.path.isdir(output_dir):
            logger.error(f"指定的输出路径不是目录: {output_dir}")
            sys.exit(1)
    
    passwords = load_passwords('passwd.yaml')
    
    if not passwords:
        logger.warning("密码列表为空，将只尝试空密码")
    
    try_passwords(archive_path, passwords, output_dir, force_mode)

if __name__ == "__main__":
    main()