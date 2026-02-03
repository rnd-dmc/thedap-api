import pandas as pd
import numpy as np
import json
from CONFIG.thedap_db import getDATA
from collections import OrderedDict
from datetime import datetime
import re

class getUTIL_v5(getDATA):
    
    def __init__(self):
        super().__init__()

    # 입력 가중치 변환
    def get_weight(self, input_weight, grps=None, reach=None, channel=None):
        weight = pd.read_json(input_weight)['input_weight'][0].strip()
        if (weight == 'auto'):
            b1 = -0.13538392
            b2 = 0.61392276
            b3 = -0.03557757

            get_weight = np.exp(-(b1 * np.log(grps) + b2 * reach + b3 * np.log(channel)))
            get_weight = (1.5 if (get_weight > 1.5) else 1.0 if (get_weight < 1.0) else get_weight)
        else:
            get_weight = (
                1.25 if (weight == "basic") else (1.0 if (weight == "low") else 1.5))
        
        # print(f"weight : {weight} / get_weight : {get_weight}")
        
        return (get_weight)


    # TV 리스트
    def get_TV_list(self):
        tv_platforms = self.parameter_DB.loc[
            self.parameter_DB['platform'].str.startswith('TV', na=False), 
            'platform'
        ].unique().tolist()
        return tv_platforms
        
    # 중복 가중치
    def trans_duplicate(self, arr, weight):
        td = 0.0
        for x in arr:
            td += x - weight * td * x
        return max(td, np.max(arr))


    # 입력 연령값 조정
    def trans_min_age(self, input_age_min):

        diff_min = (self.population_DB['age_min'] - input_age_min).drop_duplicates().abs()
        trans_min = int((self.population_DB['age_min'].drop_duplicates())[diff_min == min(diff_min)].values[0])

        return (trans_min)


    def trans_max_age(self, input_age_max):

        diff_max = (self.population_DB['age_max'] - input_age_max).drop_duplicates().abs()
        trans_max = int((self.population_DB['age_max'].drop_duplicates())[diff_max == min(diff_max)].values[0])

        return (trans_max)


    def trans_age(self, input_age):
        trans_min = self.trans_min_age(int(pd.read_json(input_age)['input_age_min'][0]))
        trans_max = self.trans_max_age(int(pd.read_json(input_age)['input_age_max'][0]))

        trans_age = pd.DataFrame({'trans_min': [trans_min], 'trans_max': [trans_max]}).to_json(force_ascii=False)
        return (trans_age)


    # 입력 성별값 조정
    def get_gender(self, input_gender):
        gender_df = pd.read_json(input_gender)

        if (gender_df['input_gender'].shape[0] > 1):
            get_gender = 'P'
        else:
            get_gender = gender_df['input_gender'].to_list()[0]

        get_gender = pd.DataFrame({'gender': [get_gender]}).to_json(force_ascii=False)

        return (get_gender)


    # 성-연령 구간별 인구모수
    def get_population(self, gender, trans_min, trans_max):

        gender_list = (['M', 'F'] if gender == 'P' else [gender])
        filt = self.population_DB[(self.population_DB.gender).isin(gender_list) & (self.population_DB.age_min >= trans_min) & (
                    self.population_DB.age_max <= trans_max)]
        trans_pop = pd.DataFrame({'trans_pop': [sum(filt.population)]}).to_json(force_ascii=False)

        return (trans_pop)


    # 연령 구간별 인구모수
    def get_age_range(self, gender, trans_min, trans_max):

        gender_list = (['M', 'F'] if gender == 'P' else [gender])
        filt = self.population_DB[
            (self.population_DB.gender).isin(gender_list) & 
            (self.population_DB.age_min >= trans_min) & 
            (self.population_DB.age_max <= trans_max)
        ].drop(['date', 'year', 'month'], axis=1)

        return (filt)


    # 타겟모수
    def get_target_info(self, input_gender, input_age):
        gender = pd.read_json(self.get_gender(input_gender))['gender'][0]
        age_min = pd.read_json(self.trans_age(input_age))['trans_min'][0]
        age_max = pd.read_json(self.trans_age(input_age))['trans_max'][0]

        df = pd.read_json(self.get_population(gender, age_min, age_max)).assign(target=str(gender) + str(age_min) + str(age_max))
        df = df[['target', 'trans_pop']].rename(columns={'trans_pop': 'target_pop'}).astype({'target_pop': 'float'})

        df_list = []
        for r in range(0, df.shape[0]):
            dt = OrderedDict()
            row_values = df.loc[r,]
            dt['target'] = row_values['target']
            dt['target_pop'] = row_values['target_pop']
            df_list.append(dt)
        j = json.loads(json.dumps(df_list, ensure_ascii=False))

        return (j)


    # 리치커브 간격
    def get_seq(self, input_seq):
        seq = pd.read_json(input_seq).iloc[0, 0]
        seq = np.where(seq == "", 10, seq)

        if (seq < 1):
            n = 1
        else:
            n = np.round(seq)

        return n


    # 리치커브 최대금액
    def get_maxbudget(self, input_maxbudget):
        maxbudget = pd.read_json(input_maxbudget).iloc[0, 0]
        maxbudget = np.where(maxbudget == "", 10, maxbudget)

        if (maxbudget == 0):
            m = 10
        else:
            m = np.round(maxbudget, 6)

        return m


    # 커버리지 확인
    def check_coverage(self, opt_mix, opt_target, input_age, input_gender):
        def weighted_mean(series, weights):
            return np.floor(((series * weights).sum() / weights.sum()) * 100) / 100

        mix_df = pd.read_json(opt_mix)
        age = pd.read_json(self.trans_age(input_age))
        trans_min = age['trans_min'][0]
        trans_max = age['trans_max'][0]
        gender_list = (['M', 'F'] if pd.read_json(self.get_gender(input_gender))['gender'][0] == 'P' else [
            pd.read_json(self.get_gender(input_gender))['gender'][0]])
        target_reach = pd.read_json(opt_target).iloc[0, 0]

        mix_df = self.parameter_DB.merge(pd.read_json(opt_mix)[['platform', 'product']]). \
            query('age_min >= {} & age_max <= {}'.format(trans_min, trans_max))
        mix_df = mix_df[mix_df['gender'].apply(lambda x: x in gender_list)].reset_index(drop=True)

        mix_df = mix_df.merge(self.distribution_DB[['platform', 'gender', 'age_min', 'age_max', 'distribution']]). \
            groupby(['platform', 'product']).apply(
            lambda x: pd.Series({
                'c': weighted_mean(x['c'], x['distribution'])
            })
        ).reset_index()

        if np.sum(mix_df['c'] > target_reach) > .0:
            return True
        else:
            return False
    
    ###
    def safe_date(self, date_str):
        if not isinstance(date_str, str):
            return None
            
        date_str = date_str.strip()

        try:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                return None
            
            datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_str
            
        except:
            return None
        
    def calc_period(self, end, start):
        try:
            if not isinstance(end, str) or not isinstance(start, str):
                return 30 
            # 날짜가 없으면 기본값 30일 설정
            d1 = datetime.strptime(end, '%Y-%m-%d')
            d2 = datetime.strptime(start, '%Y-%m-%d')
            return (d1 - d2).days + 1
        except:
            return 30

    def round_float(self, df: pd.DataFrame):
        df = df.copy()
        fcols = df.select_dtypes(include=['float', 'float64', 'float32']).columns

        if len(fcols) > 0:
            df[fcols] = df[fcols].replace([np.inf, -np.inf], 0)
            df[fcols] = df[fcols].fillna(0).round(6)
            
        return df