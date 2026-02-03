import pandas as pd
import numpy as np
import json
from CONFIG.thedap_db import getDATA
from collections import OrderedDict

class getUTIL_v4(getDATA):
    
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
        
        return (get_weight)


    # 중복 가중치
    def trans_duplicate(self, list, weight):
        trans_duplicate = 0

        for i in range(len(list)):
            trans_duplicate = trans_duplicate + list[i] - weight * trans_duplicate * list[i]
        trans_duplicate = (max(list) if (trans_duplicate < max(list)) else trans_duplicate)

        return (trans_duplicate)


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
        filt = self.population_DB[(self.population_DB.gender).isin(gender_list) & (self.population_DB.age_min >= trans_min) & (
                    self.population_DB.age_max <= trans_max)]. \
            drop(['date', 'year', 'month'], axis=1)

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
        seq = pd.read_json(input_seq)['input_seq'][0]
        seq = np.where(seq == "", 10, seq)

        if (seq < 1):
            n = 1
        else:
            n = np.round(seq)

        return n


    # 리치커브 최대금액
    def get_maxbudget(self, input_maxbudget):
        maxbudget = pd.read_json(input_maxbudget)['input_maxbudget'][0]
        maxbudget = np.where(maxbudget == "", 10, maxbudget)

        if (maxbudget == 0):
            m = 10
        else:
            m = np.round(maxbudget)

        return m
    
    def round_float(self, df: pd.DataFrame):
        df = df.copy()
        fcols = df.select_dtypes(include=['float', 'float64', 'float32']).columns

        if len(fcols) > 0:
            df[fcols] = df[fcols].replace([np.inf, -np.inf], 0)
            df[fcols] = df[fcols].fillna(0).round(6)
            
        return df