import pandas as pd
import numpy as np
from datetime import datetime, date
import json
from collections import OrderedDict
from THEDAP_SIMULATION.DapPhase3_v5 import DapPhase3_v5

class DapPhase4_v5(DapPhase3_v5):
    
    def __init__(self, inputModelDate = datetime.strftime(date.today(), "%Y-%m-%d"), userName = ''):
        super().__init__(inputModelDate=inputModelDate, userName=userName)


    # 매체별 결과
    def phase4(self, input_mix, input_age, input_gender):
        df = self.phase2(input_mix, input_age, input_gender)
        df['e_reach_p'] = np.where(df['e_reach_p'] > df['c_ovr'], df['c_ovr'], df['e_reach_p'])
        df['agrps'] = np.exp((-(df['a_ovr']) - np.log(df['c_ovr'] / (df['e_reach_p']) - 1)) / df['b_ovr'])

        max_reach = df.groupby(['platform', 'gender', 'age_min', 'age_max']).\
            agg(
                max_reach_n=('e_reach_n', 'max'), max_reach2_n=('e_reach2_n', 'max'),
                max_reach3_n=('e_reach3_n', 'max'), max_reach4_n=('e_reach4_n', 'max'),
                max_reach5_n=('e_reach5_n', 'max'), max_reach6_n=('e_reach6_n', 'max'),
                max_reach7_n=('e_reach7_n', 'max'), max_reach8_n=('e_reach8_n', 'max'),
                max_reach9_n=('e_reach9_n', 'max'), max_reach10_n=('e_reach10_n', 'max'),
                retargeting = ('retargeting', 'max'), retargeting_cnt=('retargeting_cnt', 'sum'), line_cnt = ('line_cnt', 'sum')
            ).reset_index()
        
        df = df.groupby(['platform', 'gender', 'age_min', 'age_max']). \
            agg({'e_imp': 'sum', 'eimp_weighted': 'sum', 'e_imp_a': 'sum', 'eimp_a_weighted': 'sum',
                'target_impression': 'sum', 'target_impression_weighted': 'sum', 'target_impression_a': 'sum',
                'target_impression_a_weighted': 'sum',
                'population': 'mean', 'agrps': 'sum', 'a_ovr': 'min', 'b_ovr': 'max', 'c_ovr': 'max', 'row_n': 'sum',
                'e_reach_n': 'sum', 'e_reach2_n': 'sum', 'e_reach3_n': 'sum', 'e_reach4_n': 'sum', 'e_reach5_n': 'sum',
                'e_reach6_n': 'sum', 'e_reach7_n': 'sum', 'e_reach8_n': 'sum', 'e_reach9_n': 'sum', 'e_reach10_n': 'sum',
                'ratio2_a': 'min', 'ratio2_af': 'max', 'ratio2_grps': 'max', 'ratio3_a': 'min', 'ratio3_af': 'max',
                'ratio3_grps': 'max', 'ratio4_a': 'min', 'ratio4_af': 'max', 'ratio4_grps': 'max',
                'ratio5_a': 'min', 'ratio5_af': 'max', 'ratio5_grps': 'max', 'ratio6_a': 'min', 'ratio6_af': 'max',
                'ratio6_grps': 'max', 'ratio7_a': 'min', 'ratio7_af': 'max', 'ratio7_grps': 'max',
                'ratio8_a': 'min', 'ratio8_af': 'max', 'ratio8_grps': 'max', 'ratio9_a': 'max', 'ratio9_af': 'max',
                'ratio9_grps': 'max', 'ratio10_a': 'max', 'ratio10_af': 'max', 'ratio10_grps': 'max'}).reset_index()
        df.rename(columns={'e_reach_n': 'reach_sum', 'e_reach2_n': 'reach2_sum', 'e_reach3_n': 'reach3_sum',
                        'e_reach4_n': 'reach4_sum', 'e_reach5_n': 'reach5_sum',
                        'e_reach6_n': 'reach6_sum', 'e_reach7_n': 'reach7_sum', 'e_reach8_n': 'reach8_sum',
                        'e_reach9_n': 'reach9_sum', 'e_reach10_n': 'reach10_sum'}, inplace=True)
        df = df.merge(max_reach, how='left')

        df['isDemo'] = np.where(df['e_imp'] > 0., 1, 0)
        df['isTarget'] = np.where(df['target_impression'] > 0., 1, 0)
        df['e_reach_p'] = df['c_ovr'] / (1 + np.exp(-(df['a_ovr'] + df['b_ovr'] * np.log(df['agrps']))))
        df['e_reach_p'] = np.where(
            (df['retargeting_cnt'] == df['line_cnt']) & ((df['e_reach_p'] * df['population']) > (df['retargeting'])), 
            df['retargeting'] / df['population'] * .9999,
            df['e_reach_p']
        )
        df['e_reach_n'] = df['e_reach_p'] * df['population']
        df['e_reach_n'] = np.where(df['e_reach_n'] > df['reach_sum'], df['reach_sum'], df['e_reach_n'])
        df['e_reach_p'] = np.where(df['agrps'] > 0, df['e_reach_n'] / df['population'], 0)
        df['e_reach_n'] = np.where(df['e_reach_n'] < df['max_reach_n'], df['max_reach_n'], df['e_reach_n'])
        df['e_reach_p'] = np.where(df['agrps'] > 0, df['e_reach_n'] / df['population'], 0)

        df['e_grps'] = df['eimp_weighted'] / df['population'] * 100
        df['e_grps_a'] = df['e_imp_a'] / df['population'] * 100
        df['target_grps'] = df['e_grps'] * df['isTarget']
        df['target_grps_a'] = df['e_grps_a'] * df['isTarget']
        df['target_reach_n'] = df['e_reach_n'] * df['isTarget']
        df['target_reach_p'] = df['target_reach_n'] / df['population']
        
        df['af'] = df['e_imp_a'] / df['e_reach_n']
        df['af_a'] = df['eimp_weighted'] / df['e_reach_n']
        df['target_af'] = df['target_impression_weighted'] / df['target_reach_n']
        df['target_af_a'] = df['target_impression_a'] / df['target_reach_n']

        for r in range(2, 11):
            max_reach_n = 'max_reach' + str(r) + '_n'
            e_ratio = 'e_ratio' + str(r)
            e_reach_p = 'e_reach' + str(r) + '_p'
            e_reach_n = 'e_reach' + str(r) + '_n'
            reach_sum = 'reach' + str(r) + '_sum'

            target_ratio = 'target_ratio' + str(r)
            target_reach_p = 'target_reach' + str(r) + '_p'
            target_reach_n = 'target_reach' + str(r) + '_n'

            ratio_a = 'ratio' + str(r) + '_a'
            ratio_af = 'ratio' + str(r) + '_af'
            ratio_grps = 'ratio' + str(r) + '_grps'

            ###
            df[e_ratio] = (1 / (1 + np.exp(
                -(df[ratio_a] + df[ratio_af] * np.log(df['af']) + df[ratio_grps] * np.log(df['e_grps'])))))
            df[target_ratio] = (1 / (1 + np.exp(
                -(df[ratio_a] + df[ratio_af] * np.log(df['target_af']) + df[ratio_grps] * np.log(df['target_grps'])))))

            ###
            if r == 2:
                _e_reach_p = 'e_reach_p'
                _target_reach_p = 'target_reach_p'
            else:
                _e_reach_p = 'e_reach' + str(r - 1) + '_p'
                _target_reach_p = 'target_reach' + str(r - 1) + '_p'

            df[e_reach_p] = df[_e_reach_p] * df[e_ratio]
            df[e_reach_n] = df[e_reach_p] * df['population']
            df[e_reach_n] = np.where(df[e_reach_n] < df[max_reach_n], df[max_reach_n], df[e_reach_n])
            df[e_reach_p] = df[e_reach_n] / df['population']
            
            df[target_reach_p] = df[_target_reach_p] * df[target_ratio]
            df[target_reach_n] = df[target_reach_p] * df['population']
            df[target_reach_n] = np.where(df[target_reach_n] < (df[max_reach_n] * df['isTarget']), (df[max_reach_n] * df['isTarget']), df[target_reach_n])
            df[target_reach_p] = df[target_reach_n] / df['population']

        df = self.round_float(df.fillna(.0))

        return (df)


    def summary_each_platform(self, input_mix, input_age, input_gender):
        ph4 = self.phase4(input_mix, input_age, input_gender)
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True)
        trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][0]

        df = ph4.query('e_grps_a != 0')
        df = df.groupby(['platform']). \
            agg({'e_imp': 'sum', 'eimp_weighted': 'sum', 'e_imp_a': 'sum', 'eimp_a_weighted': 'sum',
                'target_impression': 'sum', 'target_impression_weighted': 'sum', 'target_impression_a': 'sum',
                'target_impression_a_weighted': 'sum',
                'retargeting': 'sum',
                'retargeting_cnt': 'sum', 'line_cnt': 'sum',
                'e_reach_n': 'sum', 'e_reach2_n': 'sum', 'e_reach3_n': 'sum', 'e_reach4_n': 'sum', 'e_reach5_n': 'sum',
                'e_reach6_n': 'sum', 'e_reach7_n': 'sum', 'e_reach8_n': 'sum', 'e_reach9_n': 'sum', 'e_reach10_n': 'sum',
                'target_reach_n': 'sum', 'target_reach2_n': 'sum', 'target_reach3_n': 'sum', 'target_reach4_n': 'sum',
                'target_reach5_n': 'sum',
                'target_reach6_n': 'sum', 'target_reach7_n': 'sum', 'target_reach8_n': 'sum', 'target_reach9_n': 'sum',
                'target_reach10_n': 'sum',
                'population': 'sum'}).reset_index()

        df = pd.merge(df, mix_cleaned.groupby(['platform']). \
                    agg({'budget': 'sum', 'date_start': 'min', 'date_end': 'max'}).reset_index())
        
        df['e_grps_a'] = df['e_imp_a'] / df['population'] * 100
        df['e_grps'] = df['eimp_weighted'] / df['population'] * 100
        df['af_a'] = df['e_imp_a'] / df['e_reach_n']
        df['af'] = df['eimp_weighted'] / df['e_reach_n']
        
        df['target_grps_a'] = df['target_impression_a'] / trans_pop * 100
        df['target_grps'] = df['target_impression_weighted'] / trans_pop * 100
        df['target_af_a'] = df['target_impression_a'] / df['target_reach_n']
        df['target_af'] = df['target_impression_weighted'] / df['target_reach_n']

        for r in range(1, 11):
            if r == 1:
                reach = 'reach'
            else:
                reach = 'reach' + str(r)

            e_reach_p = 'e_' + reach + '_p'
            e_reach_n = 'e_' + reach + '_n'
            target_reach_p = 'target_' + reach + '_p'
            target_reach_n = 'target_' + reach + '_n'

            df[e_reach_p] = np.where(df[e_reach_n] < 1.0, 0.0, df[e_reach_n] / df['population'])
            df[target_reach_p] = np.where(df[target_reach_n] < 1.0, 0.0, df[target_reach_n] / trans_pop)

        select_columns = ['campaign', 'line', 'platform', 'product', 'date_start', 'date_end', 'gender', 'age_min',
                        'age_max', 'budget', 'target_impression_a', 'target_impression_weighted'] + \
                        [x for x in df.columns if 'target_reach' in x] + \
                        ['target_grps_a', 'target_grps', 'target_af_a', 'target_af']

        df = df.filter(select_columns). \
            rename(columns={'target_impression_a': 'target_impression',
                            'target_grps':'target_grps_weighted', 'target_grps_a': 'target_grps',
                            'target_af':'target_af_weighted', 'target_af_a': 'target_af'}). \
            fillna(0)

        # df['period'] = [((datetime.strptime(x, '%Y-%m-%d') - datetime.strptime(y, '%Y-%m-%d')).days + 1)
        #                 for x, y in zip(df['date_end'], df['date_start'])]
        df['period'] = [self.calc_period(x, y) for x, y in zip(df['date_end'], df['date_start'])]
        df['target_af_day'] = df['target_af'] / df['period']
        df['target_af_week'] = df['target_af'] / df['period'] * 7
        df['target_af_30'] = df['target_af'] / df['period'] * 30
        df['imp_interval'] = df['period'] / df['target_af']
        
        df['target_af_day_weighted'] = df['target_af_weighted'] / df['period']
        df['target_af_week_weighted'] = df['target_af_weighted'] / df['period'] * 7
        df['target_af_30_weighted'] = df['target_af_weighted'] / df['period'] * 30
        df['imp_interval_weighted'] = df['period'] / df['target_af_weighted']
        
        df['imp_interval'] = df['imp_interval'].apply(lambda x: str(np.round(x, 2)) + '일당 1회 노출')
        df['imp_interval_weighted'] = df['imp_interval_weighted'].apply(lambda x: str(np.round(x, 2)) + '일당 1회 노출')
        df = df.drop('period', axis=1).assign(line="Platform Total", campaign=None, product=None, gender=None, age_min=None,
                                            age_max=None)

        df = self.round_float(df)

        return (ph4, df)