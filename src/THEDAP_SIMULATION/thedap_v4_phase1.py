
import pandas as pd
import numpy as np
from THEDAP_UTILS.thedap_v4_mixclean import getMixClean_v4

class getPhase1_v4(getMixClean_v4):
    
    def __init__(self):
        super().__init__()
        
    ### 결과 계산에 필요한 함수
    def get_tidy(self, input_mix):
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True)
        param_npl_db_ = self.parameter_nplus_DB.filter(
            ['gender', 'age_min', 'age_max'] + [x for x in self.parameter_nplus_DB.columns if 'ratio' in x]).drop_duplicates()

        tidy = pd.DataFrame()

        for i in range(mix_cleaned.shape[0]):
            df = self.get_age_range(mix_cleaned['gender'][i], mix_cleaned['min'][i], mix_cleaned['max'][i]). \
                assign(line=str(i + 1), platform=mix_cleaned['platform'][i], product=mix_cleaned['product'][i],
                    e_imp=mix_cleaned['e_imp'][i], impact=mix_cleaned['impact'][i],
                    eimp_weighted=mix_cleaned['eimp_weighted'][i]). \
                merge(self.distribution_DB.drop(['date', 'month', 'year'], axis=1)). \
                merge(self.population_DB.drop(['date', 'month', 'year'], axis=1), how="right").fillna(0)

            df = df.merge(df.groupby('line').agg(dist_sum=('distribution', 'sum')).reset_index()). \
                merge(self.parameter_DB.drop(['date', 'year'], axis=1), how="left",
                    left_on=['platform', 'product', 'gender', 'age_min', 'age_max'],
                    right_on=['platform', 'product', 'gender', 'age_min', 'age_max']). \
                merge(param_npl_db_, how="left",
                    left_on=['gender', 'age_min', 'age_max'],
                    right_on=['gender', 'age_min', 'age_max']). \
                sort_values(['gender', 'age_min', 'age_max']). \
                eval('ratio = distribution / dist_sum').fillna(0). \
                eval('''
                    e_imp = ratio * e_imp
                    eimp_weighted = ratio * eimp_weighted''').fillna(0). \
                eval('''
                    GRPs = e_imp / population * 100
                    GRPs_weighted = eimp_weighted / population * 100''').fillna(0). \
                assign(line=str(i + 1)). \
                merge(self.parameter_DB[self.parameter_DB['product'] == 'subtotal'].drop(['date', 'year'], axis=1).rename(
                columns={'a': 'a_ovr', 'b': 'b_ovr', 'c': 'c_ovr'}),
                    how="left", on=['platform', 'gender', 'age_min', 'age_max']). \
                assign(platform=mix_cleaned['platform'][i])

            tidy = pd.concat([tidy, df]).fillna(0)

        tidy = self.round_float(tidy.rename(columns={'product_x': 'product'}).drop('product_y', axis=1))

        return (tidy)


    ## 라인별 결과값
    def phase1(self, input_mix, input_age, input_gender):
        df = self.get_tidy(input_mix)
        age = pd.read_json(self.trans_age(input_age))
        trans_min = age['trans_min'][0]
        trans_max = age['trans_max'][0]
        pop_sum = self.population_DB['population'].sum()

        gender_list = (['M', 'F'] if pd.read_json(self.get_gender(input_gender))['gender'][0] == 'P' else [
            pd.read_json(self.get_gender(input_gender))['gender'][0]])

        df['e_reach_p'] = np.where(df['GRPs_weighted'] == 0, 0,
                                df['c'] / (1 + np.exp(-(df['a'] + df['b'] * np.log(df['GRPs_weighted'])))))
        df['e_reach_n'] = df['e_reach_p'] * df['population']
        df = df.fillna(.0)
        df['e_reach_n'] = np.where(df['e_reach_n'] > df['eimp_weighted'], df['eimp_weighted'], df['e_reach_n'])

        df['isTarget'] = np.where(
            ((df['gender'].isin(gender_list)) & (df['age_min'] >= trans_min) & (df['age_max'] <= trans_max)), 1, 0)
        df['isDemo'] = np.where(df['e_imp'] != 0, 1, 0)
        
        df['target_impression'] = df['e_imp'] * df['isTarget']
        df['target_impression_weighted'] = df['eimp_weighted'] * df['isTarget']
        df['target_reach_p'] = df['e_reach_p'] * df['isTarget']
        df['target_reach_n'] = df['e_reach_n'] * df['isTarget']

        df = df.groupby(['line', 'platform', 'product', 'gender', 'age_min', 'age_max']). \
            agg({'e_reach_n': 'sum', 'e_imp': 'sum', 'eimp_weighted': 'sum', 'target_reach_n': 'sum',
                'target_impression': 'sum', 'target_impression_weighted': 'sum',
                'population': 'sum', 'isTarget': 'mean', 'isDemo': 'mean', 'a_ovr': 'min', 'b_ovr': 'max', 'c_ovr': 'max',
                'ratio2_a': 'min', 'ratio2_af': 'max', 'ratio2_grps': 'max', 'ratio3_a': 'min', 'ratio3_af': 'max',
                'ratio3_grps': 'max', 'ratio4_a': 'min', 'ratio4_af': 'max', 'ratio4_grps': 'max',
                'ratio5_a': 'min', 'ratio5_af': 'max', 'ratio5_grps': 'max', 'ratio6_a': 'min', 'ratio6_af': 'max',
                'ratio6_grps': 'max', 'ratio7_a': 'min', 'ratio7_af': 'max', 'ratio7_grps': 'max',
                'ratio8_a': 'min', 'ratio8_af': 'max', 'ratio8_grps': 'max', 'ratio9_a': 'max', 'ratio9_af': 'max',
                'ratio9_grps': 'max', 'ratio10_a': 'max', 'ratio10_af': 'max', 'ratio10_grps': 'max'}).reset_index()

        df['e_grps'] = df['e_imp'] / df['population'] * 100
        df['e_grps_weighted'] = df['eimp_weighted'] / df['population'] * 100
        df['target_grps'] = df['target_impression'] / df['population'] * 100
        df['target_grps_weighted'] = df['target_impression_weighted'] / df['population'] * 100
        
        df['e_reach_p'] = df['e_reach_n'] / df['population']
        df['target_reach_p'] = df['target_reach_n'] / df['population']
        df['af'] = df['e_imp'] / df['e_reach_n']
        df['af_weighted'] = df['eimp_weighted'] / df['e_reach_n']
        df['target_af'] = df['target_impression'] / df['target_reach_n']
        df['target_af_weighted'] = df['target_impression_weighted'] / df['target_reach_n']

        for r in range(2, 11):
            e_ratio = 'e_ratio' + str(r)
            e_reach_p = 'e_reach' + str(r) + '_p'
            e_reach_n = 'e_reach' + str(r) + '_n'

            target_ratio = 'target_ratio' + str(r)
            target_reach_p = 'target_reach' + str(r) + '_p'
            target_reach_n = 'target_reach' + str(r) + '_n'

            ratio_a = 'ratio' + str(r) + '_a'
            ratio_af = 'ratio' + str(r) + '_af'
            ratio_grps = 'ratio' + str(r) + '_grps'

            ###
            df[e_ratio] = (1 / (1 + np.exp(-(
                        df[ratio_a] + df[ratio_af] * np.log(df['af_weighted']) + df[ratio_grps] * np.log(
                    df['e_grps_weighted'])))))
            df[target_ratio] = (1 / (1 + np.exp(-(
                        df[ratio_a] + df[ratio_af] * np.log(df['target_af_weighted']) + df[ratio_grps] * np.log(
                    df['target_grps_weighted'])))))

            ###
            if r == 2:
                _e_reach_p = 'e_reach_p'
                _target_reach_p = 'target_reach_p'
            else:
                _e_reach_p = 'e_reach' + str(r - 1) + '_p'
                _target_reach_p = 'target_reach' + str(r - 1) + '_p'

            df[e_reach_p] = df[_e_reach_p] * df[e_ratio]
            df[target_reach_p] = df[_target_reach_p] * df[target_ratio]
            df[e_reach_n] = df[e_reach_p] * df['population']
            df[target_reach_n] = df[target_reach_p] * df['population']

        df.fillna(0, inplace=True)
        df = self.round_float(df)
        
        return (df)


    def summary_each_line(self, input_mix, input_age, input_gender):
        ph1 = self.phase1(input_mix, input_age, input_gender)
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True)
        trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][0]

        df = ph1.query('e_grps != 0')
        df = df.groupby(['line', 'platform', 'product']). \
            agg({'age_min': 'min', 'age_max': 'max', 'e_imp': 'sum', 'eimp_weighted': 'sum', 'target_impression': 'sum',
                'target_impression_weighted': 'sum', 'population': 'sum',
                'e_reach_n': 'sum', 'e_reach2_n': 'sum', 'e_reach3_n': 'sum', 'e_reach4_n': 'sum', 'e_reach5_n': 'sum',
                'e_reach6_n': 'sum', 'e_reach7_n': 'sum', 'e_reach8_n': 'sum', 'e_reach9_n': 'sum', 'e_reach10_n': 'sum',
                'target_reach_n': 'sum', 'target_reach2_n': 'sum', 'target_reach3_n': 'sum', 'target_reach4_n': 'sum',
                'target_reach5_n': 'sum',
                'target_reach6_n': 'sum', 'target_reach7_n': 'sum', 'target_reach8_n': 'sum', 'target_reach9_n': 'sum',
                'target_reach10_n': 'sum'}).reset_index()

        df = df.merge(mix_cleaned[['line', 'budget', 'gender']])
        
        df['e_grps'] = df['e_imp'] / df['population'] * 100
        df['e_grps_weighted'] = df['eimp_weighted'] / df['population'] * 100
        df['af'] = df['e_imp'] / df['e_reach_n']
        df['af_weighted'] = df['eimp_weighted'] / df['e_reach_n']
        
        df['target_grps'] = df['target_impression'] / trans_pop * 100
        df['target_grps_weighted'] = df['target_impression_weighted'] / trans_pop * 100
        df['target_af'] = df['target_impression'] / df['target_reach_n']
        df['target_af_weighted'] = df['target_impression_weighted'] / df['target_reach_n']

        for r in range(1, 11):
            if r == 1:
                reach = 'reach'
            else:
                reach = 'reach' + str(r)

            e_reach_p = 'e_' + reach + '_p'
            e_reach_n = 'e_' + reach + '_n'
            target_reach_p = 'target_' + reach + '_p'
            target_reach_n = 'target_' + reach + '_n'

            df[e_reach_p] = df[e_reach_n] / df['population']
            df[target_reach_p] = df[target_reach_n] / trans_pop

        df = df[['line', 'platform', 'product', 'gender', 'age_min', 'age_max', 'budget',
                'target_impression', 'target_impression_weighted', 'target_grps', 'target_grps_weighted', 'target_reach_n', 'target_reach_p',
                'target_af', 'target_af_weighted']]. \
            fillna(0)

        df = df.merge(mix_cleaned[['line', 'gender_org', 'min_org', 'max_org', 'platform', 'product', 'budget']])
        df['gender'] = df['gender_org']
        df['age_min'] = df['min_org']
        df['age_max'] = df['max_org']
        df.drop(['gender_org', 'min_org', 'max_org'], axis=1, inplace=True)
        df = self.round_float(df)
        
        return (ph1, df)

