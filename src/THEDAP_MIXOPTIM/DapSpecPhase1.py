import warnings
import pandas as pd
import numpy as np
from datetime import datetime

warnings.filterwarnings(action='ignore')
from dateutil.relativedelta import relativedelta

from THEDAP_SIMULATION.DapPhase5_v5 import DapPhase5_v5

class DapSpecPhase1(DapPhase5_v5):
    
    def __init__(self):
        super().__init__()

    def spec_tidy(self, spec_mixpair, input_age, input_gender, spec_seq, spec_maxbudget):
        mix_a = pd.DataFrame(pd.DataFrame(spec_mixpair).loc[0, 'mix_a']).assign(campaign='mix_a')
        mix_b = pd.DataFrame(pd.DataFrame(spec_mixpair).loc[0, 'mix_b']).assign(campaign='mix_b')
        spec_mix = pd.concat([mix_a, mix_b], axis=0).reset_index(drop=True)

        age = pd.read_json(self.trans_age(input_age))
        trans_min = age['trans_min'][0]
        trans_max = age['trans_max'][0]

        # 최적화 범위
        seq = self.get_seq(spec_seq)
        maxbudget = self.get_maxbudget(spec_maxbudget)

        spec_range = [np.round(x) for x in
                    list(np.arange(0, (maxbudget * 1e+06) + (maxbudget * 1e+06 / seq), maxbudget * 1e+06 / seq))]
        spec_range = [x for x in spec_range if x <= np.round(maxbudget * 1e+06)]
        if (len(spec_range) <= seq):
            spec_range.insert(len(spec_range), np.round(maxbudget * 1e+06))

        if (spec_range[-1] != np.round(maxbudget * 1e+06)):
            spec_range[-1] = np.round(maxbudget * 1e+06)

        spec_mix_cleaned = spec_mix.assign(
            date_start=datetime.today().strftime('%Y-%m-%d'),
            date_end=(datetime.today() + relativedelta(months=+1)).strftime('%Y-%m-%d'),
            gender=pd.read_json(self.get_gender(input_gender))['gender'][0],
            min=trans_min,
            max=trans_max,
            retargeting=.0,
            budget=maxbudget,
            imp=.0,
            reach=.0
        ).to_json(orient='records', force_ascii=False)
        spec_mix_cleaned = self.mix_clean(spec_mix_cleaned).assign(budget=.0)

        spec_mix_concat = pd.DataFrame()
        for i in range(seq + 1):
            spec_mix_concat = pd.concat([spec_mix_concat,
                                        spec_mix_cleaned.assign(
                                            maxbudget=maxbudget * 1e+06,
                                            ratio_a=1 - (i / seq))])

        spec_mix_concat['budget'] = np.where(spec_mix_concat['campaign'] == 'mix_a',
                                            spec_mix_concat['maxbudget'] * spec_mix_concat['ratio_a'] * spec_mix_concat[
                                                'alloc_rat'],
                                            spec_mix_concat['maxbudget'] * (1.0 - spec_mix_concat['ratio_a']) *
                                            spec_mix_concat['alloc_rat'])

        spec_mix_concat['mix'] = spec_mix_concat['campaign']
        spec_mix_concat['campaign'] = ['미디어믹스A {:,.0f}% - 미디어믹스B {:,.0f}%'.format(r * 100, (1 - r) * 100) for r in
                                    spec_mix_concat['ratio_a']]
        spec_mix_concat = spec_mix_concat.reset_index(drop=True).drop(['maxbudget', 'ratio_a'], axis=1)

        return spec_mix_concat


    def spec_phase1(self, spec_mixpair, input_age, input_gender, input_weight, spec_seq, spec_maxbudget):
        spec_mix_concat = self.spec_tidy(spec_mixpair, input_age, input_gender, spec_seq, spec_maxbudget)
        spec_mix_concat = spec_mix_concat.iloc[:, :15].assign(imp=.0, reach=.0). \
            to_json(orient='records', force_ascii=False)

        _3, summary_camp_ = self.summary_each_campaign(input_mix=spec_mix_concat, input_age=input_age, input_gender=input_gender,
                                                input_weight=input_weight)

        summary_camp_['mix_a'] = [c.split(' - ')[0].replace('미디어믹스A ', '') for c in summary_camp_['campaign']]
        summary_camp_['mix_b'] = [c.split(' - ')[1].replace('미디어믹스B ', '') for c in summary_camp_['campaign']]
        summary_camp_['idx'] = summary_camp_['mix_a'].str.extract(r'(\d+)')
        summary_camp_['idx'] = summary_camp_['idx'].apply(lambda x: float(x))

        spec_result = summary_camp_.filter(
            ['idx', 'mix_a', 'mix_b', 'target_grps', 'target_grps_weighted', 'target_af'] + \
            [x for x in summary_camp_.columns if 'target_reach' in x]
        ).sort_values('idx', ascending=True).drop('idx', axis=1).reset_index(drop=True)

        spec_idx = spec_result.filter([x for x in spec_result.columns if '_p' in x]).apply(
            lambda x: np.round(x * 100 / np.max(x), 2), axis=0)
        spec_idx.columns = [c.replace('_p', '_idx') for c in spec_idx.columns]
        spec_n = spec_result.filter([x for x in spec_result.columns if '_n' in x]).apply(lambda x: np.round(x), axis=0)
        spec_result = spec_result.drop([x for x in spec_n.columns], axis=1)
        spec_result = pd.concat([spec_result, spec_n, spec_idx], axis=1)

        result = {}
        cols_dict = {'_p': 'reach_p', '_n': 'reach_n', '_idx': 'reach_scaled'}

        for f in cols_dict.keys():
            cols_ = ['mix_a', 'mix_b', 'target_grps', 'target_grps_weighted', 'target_af'] + [x for x in spec_result.columns if f in x]
            result_ = spec_result.filter(cols_)

            keys_ = cols_dict[f]
            vals_ = result_.to_dict(orient='records')
            result[keys_] = vals_

            #### 상단 시각화
        viz_df = spec_result.reset_index()
        viz_df['A'] = [float(x.replace('%', '')) for x in spec_result['mix_a']]
        viz_df['B'] = [float(x.replace('%', '')) for x in spec_result['mix_b']]

        viz_df['x_ticks'] = np.where(viz_df['A'] < viz_df['B'], 'B ' + viz_df['mix_b'], 'A ' + viz_df['mix_a'])
        viz = viz_df.astype({'index': 'float'}).rename(columns={'index': 'idx'}). \
            filter(['idx', 'x_ticks', 'target_reach_idx', 'target_reach3_idx']). \
            to_dict(orient='records')

        return [viz, result]