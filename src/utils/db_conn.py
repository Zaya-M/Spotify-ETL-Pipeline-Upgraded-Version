# ============================================================
# 文件：src/utils/db_conn.py
# 作用：数据库连接管理，使用连接池避免频繁建立/断开连接
# 环境：需要 pymysql、sqlalchemy、python-dotenv
# ============================================================
import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from src.utils.logger import get_logger

load_dotenv()  # 读取 .env 文件中的环境变量

logger = get_logger(__name__)


class DBConnection:
    """
    数据库连接管理类
    使用单例模式，整个项目只创建一个连接池
    """

    _engine = None  # 类变量，存储连接引擎（单例）

    @classmethod
    def get_engine(cls):
        """
        获取数据库连接引擎（懒加载，第一次调用时才创建）
        用法：
            engine = DBConnection.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
        """

        if cls._engine is None:
            # TODO: 从环境变量读取数据库配置
            # 提示：os.getenv("MYSQL_HOST", "localhost")
            # 需要读取：MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
            user = os.getenv("MYSQL_USER")
            password = os.getenv("MYSQL_PASSWORD")
            host = os.getenv("MYSQL_HOST", "localhost")
            port = os.getenv("MYSQL_PORT", "3306")
            database = os.getenv("MYSQL_DATABASE")

            # TODO: 构建连接字符串
            # 格式：mysql+pymysql://user:password@host:port/database?charset=utf8mb4
            conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"

            try:

                # TODO: 创建 engine，配置连接池
                # 提示：create_engine(conn_str, poolclass=QueuePool, pool_size=5, max_overflow=10)
                cls._engine = create_engine(
                    conn_str,
                    poolclass=QueuePool,
                    pool_size=5,  # 初始连接数
                    max_overflow=10,  # 最大溢出连接数
                    pool_timeout=30,  # 超时时间
                    pool_recycle=3600,  # 每小时自动回收连接防止 MySQL 断开
                )

                # TODO: 测试连接是否成功，成功则 logger.info，失败则 logger.error 并抛出异常
                with cls._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"Successfully connected to MySQL database: {database}")

            except Exception as e:
                logger.error(f"Failed to create database engine: {e}")
                cls._engine = None
                raise e

        return cls._engine

    @classmethod
    def execute_sql_file(cls, sql_file_path: str):
        """
        执行 SQL 文件（用于初始化建表）
        用法：DBConnection.execute_sql_file("sql/ods/create_ods_tables.sql")
        """
        engine = cls.get_engine()

        try:

            # TODO: 读取 SQL 文件内容
            # 提示：open(sql_file_path, 'r', encoding='utf-8').read()
            with open(sql_file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            # TODO: 按分号拆分成多条 SQL 语句，逐条执行
            # 注意：过滤掉空语句
            queries = [q.strip() for q in sql_content.split(";") if q.strip()]

            with engine.connect() as conn:
                for query in queries:
                    conn.execute(text(query))
                    conn.commit()  # 确保提交更改

            # TODO: 用 logger 记录每条 SQL 的执行情况
            logger.info(f"Executed SQL file successfully: {sql_file_path}")

        except Exception as e:
            logger.error(f"Error executing SQL file {sql_file_path}: {e}")
            raise e


# ============================================================
# 快速测试：直接运行这个文件验证连接是否成功
# 在终端执行：python src/utils/db_conn.py
# ============================================================
if __name__ == "__main__":
    logger = get_logger("db_test")
    try:
        engine = DBConnection.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"MySQL 连接成功！版本：{version}")
    except Exception as e:
        logger.error(f"连接失败：{e}")
