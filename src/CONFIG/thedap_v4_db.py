# pip install mysql-connector-python
import mysql.connector
import pandas as pd
import CONFIG.config as CONFIG

# 데이터베이스 연결
def getConnection():
    conn = mysql.connector.connect(user=CONFIG.DB_USER, password=CONFIG.DB_PASSWD, host=CONFIG.DB_HOST, database=CONFIG.DB_DATABASE)
    return conn
    
class getDATA():

    def __init__(self):
        self.population_DB = self.getPopulation()
        self.parameter_DB = self.getParameter()
        self.distribution_DB = self.getDistribution()
        self.parameter_nplus_DB = self.getNPlusParameter()
        
        # 모든 float type에 대한 반올림 (ROUND(6))
        fcols_param = self.parameter_DB.select_dtypes('float').columns
        self.parameter_DB[fcols_param] = self.parameter_DB[fcols_param].round(6)
        
        fcols_dist = self.distribution_DB.select_dtypes('float').columns
        self.distribution_DB[fcols_dist] = self.distribution_DB[fcols_dist].round(6)
        
        fcols_param_npl = self.parameter_nplus_DB.select_dtypes('float').columns
        self.parameter_nplus_DB[fcols_param_npl] = self.parameter_nplus_DB[fcols_param_npl].round(6)
        
    # 인구모수 DB
    def getPopulation(self):
        print('query_read')
        cnx = getConnection()
        # 쿼리문
        query = '''
        SELECT
            STR_TO_DATE(BASIS_DT, '%Y%m%d') as date,
            SUBSTR(BASIS_DT, 1, 4) as year,
            SUBSTR(BASIS_DT, 5, 2) as month,
            GENDER as gender,
            AGE_MIN as age_min,
            AGE_MAX as age_max,
            POPULATION as population
        FROM DAP_POPULATION
        WHERE (BASIS_DT, GENDER, AGE_MIN, AGE_MAX) IN (
        SELECT
            MAX(BASIS_DT) DATE, GENDER, AGE_MIN, AGE_MAX
        FROM DAP_POPULATION
        GROUP BY GENDER, AGE_MIN, AGE_MAX
        )'''

        # 쿼리 실행 및 결과를 DataFrame으로 변환
        df = pd.read_sql(query, cnx)

        # 연결 종료
        cnx.close()
        
        return df

    # 인구분포 DB
    def getDistribution(self):
        cnx = getConnection()
        # 쿼리문
        query = '''
        SELECT
            STR_TO_DATE(BASIS_DT, '%Y%m%d') as date,
            SUBSTR(BASIS_DT, 1, 4) as year,
            SUBSTR(BASIS_DT, 5, 2) as month,
            PLATFORM as platform,
            GENDER as gender,
            AGE_MIN as age_min,
            AGE_MAX as age_max,
            DISTRIBUTION as distribution
        FROM DAP_DISTRIBUTION
        WHERE (BASIS_DT, PLATFORM, GENDER, AGE_MIN, AGE_MAX) IN (
        SELECT
            MAX(BASIS_DT) DATE, PLATFORM, GENDER, AGE_MIN, AGE_MAX
        FROM DAP_DISTRIBUTION
        GROUP BY PLATFORM, GENDER, AGE_MIN, AGE_MAX
        )'''

        # 쿼리 실행 및 결과를 DataFrame으로 변환
        df = pd.read_sql(query, cnx)

        # 연결 종료
        cnx.close()
            
        return df

    # 계수 DB
    def getParameter(self):
        cnx = getConnection()
        # 쿼리문
        query = '''
        SELECT
            STR_TO_DATE(BASIS_DT, '%Y%m%d') as date,
            SUBSTR(BASIS_DT, 1, 4) as year,
            PLATFORM as platform,
            PRODUCT as product,
            GENDER as gender,
            AGE_MIN as age_min,
            AGE_MAX as age_max,
            A_VAL as a,
            B_VAL as b,
            C_VAL as c
        FROM DAP_PARAMETER
        WHERE (BASIS_DT, PLATFORM, PRODUCT, GENDER, AGE_MIN, AGE_MAX) IN (
        SELECT
            MAX(BASIS_DT) DATE, PLATFORM, PRODUCT, GENDER, AGE_MIN, AGE_MAX
        FROM DAP_PARAMETER
        GROUP BY PLATFORM, PRODUCT, GENDER, AGE_MIN, AGE_MAX
        )'''

        # 쿼리 실행 및 결과를 DataFrame으로 변환
        df = pd.read_sql(query, cnx)

        # 연결 종료
        cnx.close()
            
        
        return pd.concat([df], ignore_index=True)

    # NPlus계수 DB
    def getNPlusParameter(self):
        cnx = getConnection()
        # 쿼리문
        query = '''
        SELECT
            STR_TO_DATE(BASIS_DT, '%Y%m%d') as date,
            SUBSTR(BASIS_DT, 1, 4) as year,
            PLATFORM as platform,
            PRODUCT as product,
            GENDER as gender,
            AGE_MIN as age_min,
            AGE_MAX as age_max,
            RATIO2_A as ratio2_a, RATIO2_AF as ratio2_af, RATIO2_GRPS as ratio2_grps,
            RATIO3_A as ratio3_a, RATIO3_AF as ratio3_af, RATIO3_GRPS as ratio3_grps,
            RATIO4_A as ratio4_a, RATIO4_AF as ratio4_af, RATIO4_GRPS as ratio4_grps,
            RATIO5_A as ratio5_a, RATIO5_AF as ratio5_af, RATIO5_GRPS as ratio5_grps,
            RATIO6_A as ratio6_a, RATIO6_AF as ratio6_af, RATIO6_GRPS as ratio6_grps,
            RATIO7_A as ratio7_a, RATIO7_AF as ratio7_af, RATIO7_GRPS as ratio7_grps,
            RATIO8_A as ratio8_a, RATIO8_AF as ratio8_af, RATIO8_GRPS as ratio8_grps,
            RATIO9_A as ratio9_a, RATIO9_AF as ratio9_af, RATIO9_GRPS as ratio9_grps,
            RATIO10_A as ratio10_a, RATIO10_AF as ratio10_af, RATIO10_GRPS as ratio10_grps
        FROM DAP_NPLUS_PARAMETER
        WHERE (BASIS_DT, PLATFORM, PRODUCT, GENDER, AGE_MIN, AGE_MAX) IN (
        SELECT
            MAX(BASIS_DT) DATE, PLATFORM, PRODUCT, GENDER, AGE_MIN, AGE_MAX
        FROM DAP_NPLUS_PARAMETER
        GROUP BY PLATFORM, PRODUCT, GENDER, AGE_MIN, AGE_MAX
        )'''

        # 쿼리 실행 및 결과를 DataFrame으로 변환
        df = pd.read_sql(query, cnx)

        # 연결 종료
        cnx.close()
        
        return df

    # 매체, 상품 데이터 조회
    def getMediaProduct(self):
        cnx = getConnection()
        # 쿼리문
        query = '''
        SELECT 
            *
        FROM VW_SERVICE_PRODUCT
            ORDER BY PLATFORM, CASE WHEN PRODUCT = 'overall' THEN 0 ELSE 1 END, PRODUCT
        '''

        # 쿼리 실행 및 결과를 DataFrame으로 변환
        df = pd.read_sql(query, cnx)

        # 연결 종료
        cnx.close()

        return df

    #
    # main
    #
    # if __name__ == '__main__':

    #     result = getPopulation()
    #     print(result)
