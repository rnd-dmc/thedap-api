import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from THEDAP_SIMULATION.thedap_v5_phase5 import getPhase5_v5


class THEDAP_OUTPUT_v5(getPhase5_v5):

    def __init__(self, input_mix, input_age, input_gender, input_weight):
        super().__init__()
        self.target = self.get_target_info(input_gender, input_age)
        self.trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                     pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                     pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][
            0]
        self.heatmap1, self.summary_line = self.summary_each_line(input_mix, input_age, input_gender)
        self.heatmap2, self.summary_subtotal = self.summary_each_subtotal(input_mix, input_age, input_gender)
        self.heatmap3, self.summary_campaign = self.summary_each_campaign(input_mix, input_age, input_gender, input_weight)
        self.heatmap4, self.summary_platform = self.summary_each_platform(input_mix, input_age, input_gender)
        self.heatmap5, self.summary_tot = self.summary_total(input_mix, input_age, input_gender, input_weight)

    ### 타겟정보
    def target_info(self):
        return self.target

    ### 라인별 결과
    def result_summary(self):
        summary_line = self.summary_line.assign(ind_n=1)
        summary_subtotal = self.summary_subtotal.assign(ind_n=2)
        summary_campaign = self.summary_campaign.assign(ind_n=3)
        summary_platform = self.summary_platform.assign(ind_n=4)
        summary_tot = self.summary_tot.assign(ind_n=5)
        df = pd.concat([summary_line, summary_subtotal, summary_campaign, summary_platform, summary_tot]).reset_index(
            drop=True).astype({'budget': 'float'})

        df['ind_n'] = df['ind_n'].apply(
            lambda x: '00' + str(x) if len(str(x)) == 1 else '0' + str(x) if len(str(x)) == 2 else str(x))
        platform_ind = summary_line[['platform', 'line']].groupby('platform').head(1).rename(columns={'line': 'ind_n2'})
        platform_ind['ind_n2'] = platform_ind['ind_n2'].apply(
            lambda x: '00' + str(x) if len(str(x)) == 1 else '0' + str(x) if len(str(x)) == 2 else str(x))
        campaign_ind = summary_line[['campaign', 'line']].groupby('campaign').head(1).rename(columns={'line': 'ind_n3'})
        campaign_ind['ind_n3'] = campaign_ind['ind_n3'].apply(
            lambda x: '00' + str(x) if len(str(x)) == 1 else '0' + str(x) if len(str(x)) == 2 else str(x))

        df = df.merge(platform_ind, how='left', on='platform'). \
            merge(campaign_ind, how='left', on='campaign').sort_values(['ind_n3', 'ind_n2', 'ind_n']). \
            drop(['ind_n', 'ind_n2', 'ind_n3'], axis=1).reset_index(drop=True)

        select_columns = ['line', 'campaign', 'platform', 'product', 'gender', 'age_min', 'age_max', 'budget',
                          'date_start', 'date_end', 'target_impression', 'target_impression_weighted', 'target_grps', 'target_grps_weighted'] + \
                        [x for x in df.columns if '_n' in x] + \
                        [x for x in df.columns if '_p' in x] + \
                        [x for x in df.columns if '_af' in x] + \
                        ['imp_interval', 'imp_interval_weighted']
                        
        except_columns = ['day_weighted', 'week_weighted', '30_weighted', 'interval_weighted']
        select_columns = [col for col in select_columns if not any(exc in col for exc in except_columns)]
        
        df = df.filter(select_columns)

        for c in ['target_impression', 'target_impression_weighted'] + [x for x in df.columns if '_n' in x]:
            df[c] = df[c].apply(lambda x: np.round(x))

        df_list = []
        for r in range(0, df.shape[0]):
            dt = OrderedDict()
            row_values = df.loc[r,]

            for c in df.columns:
                dt[c] = row_values[c]
            df_list.append(dt)
        j = json.loads(json.dumps(df_list, ensure_ascii=False))

        return (j)

    ### 히트맵
    def heatmap(self):
        heatmap1 = self.heatmap1[['line', 'gender', 'age_min', 'age_max', 'e_reach_n', 'e_reach_p', 'e_grps_a']]. \
            astype({'age_min': 'str', 'age_max': 'str'}).rename(columns={'e_grps_a': 'e_grps', 'line': 'stand'}).astype(
            {'stand': 'str'})
        heatmap1['e_reach_n'] = np.round(heatmap1['e_reach_n'])
        heatmap1['e_grps'] = np.round(heatmap1['e_grps'], 2)
        heatmap1['stand'] = 'Line ' + heatmap1['stand'] + ' 기준'
        heatmap1['age'] = (heatmap1['age_min']) + '-' + (heatmap1['age_max'])
        heatmap1.drop(['age_min', 'age_max'], axis=1, inplace=True)
        heatmap1 = heatmap1[['stand', 'gender', 'age', 'e_reach_n', 'e_reach_p', 'e_grps']]

        heatmap4 = self.heatmap4[['platform', 'gender', 'age_min', 'age_max', 'e_reach_n', 'e_reach_p', 'e_grps_a']]. \
            astype({'age_min': 'str', 'age_max': 'str'}).rename(columns={'e_grps_a': 'e_grps', 'platform': 'stand'})
        heatmap4['e_reach_n'] = np.round(heatmap4['e_reach_n'])
        heatmap4['e_grps'] = np.round(heatmap4['e_grps'], 2)
        heatmap4['stand'] = '매체별 - ' + heatmap4['stand'] + ' 기준'
        heatmap4['age'] = (heatmap4['age_min']) + '-' + (heatmap4['age_max'])
        heatmap4.drop(['age_min', 'age_max'], axis=1, inplace=True)
        heatmap4 = heatmap4[['stand', 'gender', 'age', 'e_reach_n', 'e_reach_p', 'e_grps']]

        heatmap5 = self.heatmap5[['gender', 'age_min', 'age_max', 'e_reach_n', 'e_reach_p', 'e_grps_a']]. \
            astype({'age_min': 'str', 'age_max': 'str'}).rename(columns={'e_grps_a': 'e_grps'}).assign(
            stand='미디어믹스 전체기준')
        heatmap5['e_reach_n'] = np.round(heatmap5['e_reach_n'])
        heatmap5['e_grps'] = np.round(heatmap5['e_grps'], 2)
        heatmap5['age'] = (heatmap5['age_min']) + '-' + (heatmap5['age_max'])
        heatmap5.drop(['age_min', 'age_max'], axis=1, inplace=True)
        heatmap5 = heatmap5[['stand', 'gender', 'age', 'e_reach_n', 'e_reach_p', 'e_grps']]

        df = pd.concat([heatmap1, heatmap4, heatmap5]).reset_index(drop=True).astype(
            {'e_reach_n': 'float', 'e_grps': 'float'})
        df['age'] = df['age'].apply(lambda x: str(x).replace('7-', '07-'))

        htmap = []
        dic = {"e_reach_p": "P", "e_reach_n": "N", "e_grps": "GRP"}
        for i, h in enumerate(df['stand'].unique()):
            htmap.append(dict())
            htmap[i]['name'] = h

            for j, p in enumerate(dic):
                pv = pd.DataFrame()
                pv = df.loc[df['stand'] == h].pivot(index='age', columns='gender',
                                                    values=list(dic.keys())[j]).reset_index()

                pv_list = []
                for r in range(0, pv.shape[0]):
                    dt = OrderedDict()
                    row_values = pv.loc[r,]
                    dt["age"] = row_values["age"]
                    dt["F"] = row_values["F"]
                    dt["M"] = row_values["M"]
                    pv_list.append(json.loads(json.dumps(dt, ensure_ascii=False)))
                    res = pv_list
                    htmap[i][dic[str(p)]] = res

        return (htmap)

    ### 도달 빈도분포
    def reach_freq(self):
        summary_tot = self.summary_tot
        df = pd.DataFrame({'reach': list(range(0, 11)),
                           'reach_p': [1, summary_tot['target_reach_p'][0], summary_tot['target_reach2_p'][0],
                                       summary_tot['target_reach3_p'][0], summary_tot['target_reach4_p'][0],
                                       summary_tot['target_reach5_p'][0], summary_tot['target_reach6_p'][0],
                                       summary_tot['target_reach7_p'][0], summary_tot['target_reach8_p'][0],
                                       summary_tot['target_reach9_p'][0], summary_tot['target_reach10_p'][0]]}).astype(
            {'reach': 'str'})
        df['reach_p_diff'] = (np.abs(df['reach_p'].diff(-1)))
        df['reach_p_diff'][10] = 0

        df_list = []
        for r in range(0, df.shape[0]):
            dt = OrderedDict()
            row_values = df.loc[r,]
            dt['reach'] = row_values['reach']
            dt['reach_p'] = row_values['reach_p']
            dt['reach_p_diff'] = row_values['reach_p_diff']
            df_list.append(dt)
        j = json.loads(json.dumps(df_list, ensure_ascii=False))

        return (j)

    ### 분석결과 요약
    def result_overall(self):
        summary_tot = self.summary_tot
        trans_pop = self.trans_pop

        res = [{
            "R1_p": summary_tot['target_reach_p'][0],
            "R3_p": summary_tot['target_reach3_p'][0],
            "GRPs": summary_tot['target_grps'][0],
            "AF": summary_tot['target_af'][0],
            "R1_n": np.round(summary_tot['target_reach_n'][0], 0),
            "R3_n": np.round(summary_tot['target_reach3_p'][0] * trans_pop),
        }]

        j = json.loads(json.dumps(res, ensure_ascii=True))

        return (j)

    def get_result(self):
        result = {}
        result['result_summary'] = self.result_summary()
        result['reach_heatmap'] = self.heatmap()
        result['reach_freq'] = self.reach_freq()
        result['result_overall'] = self.result_overall()

        return result