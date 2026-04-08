from src.utils.db_conn import DBConnection


def init_project_tables():
    # 路径要和你项目结构对应
    sql_path = "sql/ods/create_ods_tables.sql"
    print(f"正在执行建表脚本: {sql_path}...")
    DBConnection.execute_sql_file(sql_path)
    print("ODS 层表结构初始化完成！")


if __name__ == "__main__":
    init_project_tables()
