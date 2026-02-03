import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from THEDAP_SIMULATION.thedap_v4_phase3 import getPhase3_v4
# from THEDAP_UTILS.thedap_v4_mixclean import *


class THEDAP_OUTPUT_v4(getPhase3_v4):
    
    def __init__(self, input_mix, input_age, input_gender, input_weight):
        super().__init__()
            
    # def __init__(self, input_mix, input_age, input_gender, input_weight):
        self.target = self.get_target_info(input_gender, input_age)
        self.trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                     pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                     pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][
            0]
        self.heatmap1, self.summary_line = self.summary_each_line(input_mix, input_age, input_gender)
        self.heatmap2, self.summary_platform = self.summary_each_platform(input_mix, input_age, input_gender)
        self.heatmap3, self.summary_ovr = self.summary_overall(input_mix, input_age, input_gender, input_weight)

    ### 타겟정보
    def target_info(self):
        return self.target

    ### 라인별 결과
    def result_summary(self):
        summary_line = self.summary_line.assign(ind_n=1)
        summary_platform = self.summary_platform.assign(ind_n=2)
        summary_ovr = self.summary_ovr[
            ['budget', 'target_impression', 'target_impression_weighted', 'target_grps', 'target_grps_weighted', 'target_reach_n', 'target_reach_p', 'target_af', 'target_af_weighted', 'line']]. \
            assign(platform=None, product=None, gender=None, age_min=None, age_max=None, ind_n=3)
        df = pd.concat([summary_line, summary_platform, summary_ovr]).reset_index(drop=True).astype({'budget': 'float'})

        df['ind_n'] = df['ind_n'].apply(
            lambda x: '00' + str(x) if len(str(x)) == 1 else '0' + str(x) if len(str(x)) == 2 else str(x))
        platform_ind = summary_line[['platform', 'line']].groupby('platform').head(1).rename(columns={'line': 'ind_n2'})
        platform_ind['ind_n2'] = platform_ind['ind_n2'].apply(
            lambda x: '00' + str(x) if len(str(x)) == 1 else '0' + str(x) if len(str(x)) == 2 else str(x))
        df['target_impression_weighted'] = np.round(df['target_impression_weighted'])
        df['target_impression'] = np.round(df['target_impression'])
        df['target_reach_n'] = np.round(df['target_reach_n'])

        df = df.merge(platform_ind, how='left', on='platform').sort_values(['ind_n2', 'ind_n']). \
            drop(['ind_n', 'ind_n2'], axis=1).reset_index(drop=True)
            
        df_list = []
        for r in range(0, df.shape[0]):
            dt = OrderedDict()
            row_values = df.loc[r,]
            dt['line'] = row_values['line']
            dt['platform'] = row_values['platform']
            dt['product'] = row_values['product']
            dt['gender'] = row_values['gender']
            dt['age_min'] = row_values['age_min']
            dt['age_max'] = row_values['age_max']
            dt['budget'] = row_values['budget']
            dt['target_impression'] = row_values['target_impression']
            dt['target_impression_weighted'] = row_values['target_impression_weighted']
            dt['target_grps'] = row_values['target_grps']
            dt['target_grps_weighted'] = row_values['target_grps_weighted']
            dt['target_reach_n'] = row_values['target_reach_n']
            dt['target_reach_p'] = row_values['target_reach_p']
            dt['target_af'] = row_values['target_af']
            df_list.append(dt)
        j = json.loads(json.dumps(df_list, ensure_ascii=False))

        return (j)

    ### 히트맵
    def heatmap(self):
        heatmap1 = self.heatmap1[['line', 'gender', 'age_min', 'age_max', 'e_reach_n', 'e_reach_p', 'e_grps']]. \
            astype({'age_min': 'str', 'age_max': 'str'}).rename(columns={'line': 'stand'}).astype({'stand': 'str'})
        heatmap1['e_reach_n'] = np.round(heatmap1['e_reach_n'])
        heatmap1['e_grps'] = np.round(heatmap1['e_grps'], 2)
        heatmap1['stand'] = 'Line ' + heatmap1['stand'] + ' 기준'
        heatmap1['age'] = (heatmap1['age_min']) + '-' + (heatmap1['age_max'])
        heatmap1.drop(['age_min', 'age_max'], axis=1, inplace=True)
        heatmap1 = heatmap1[['stand', 'gender', 'age', 'e_reach_n', 'e_reach_p', 'e_grps']]

        heatmap2 = self.heatmap2[['platform', 'gender', 'age_min', 'age_max', 'e_reach_n', 'e_reach_p', 'e_grps']]. \
            astype({'age_min': 'str', 'age_max': 'str'}).rename(columns={'platform': 'stand'})
        heatmap2['e_reach_n'] = np.round(heatmap2['e_reach_n'])
        heatmap2['e_grps'] = np.round(heatmap2['e_grps'], 2)
        heatmap2['stand'] = '매체별 - ' + heatmap2['stand'] + ' 기준'
        heatmap2['age'] = (heatmap2['age_min']) + '-' + (heatmap2['age_max'])
        heatmap2.drop(['age_min', 'age_max'], axis=1, inplace=True)
        heatmap2 = heatmap2[['stand', 'gender', 'age', 'e_reach_n', 'e_reach_p', 'e_grps']]

        heatmap3 = self.heatmap3[['gender', 'age_min', 'age_max', 'e_reach_n', 'e_reach_p', 'e_grps']]. \
            astype({'age_min': 'str', 'age_max': 'str'}).assign(stand='미디어믹스 전체기준')
        heatmap3['e_reach_n'] = np.round(heatmap3['e_reach_n'])
        heatmap3['e_grps'] = np.round(heatmap3['e_grps'], 2)
        heatmap3['age'] = (heatmap3['age_min']) + '-' + (heatmap3['age_max'])
        heatmap3.drop(['age_min', 'age_max'], axis=1, inplace=True)
        heatmap3 = heatmap3[['stand', 'gender', 'age', 'e_reach_n', 'e_reach_p', 'e_grps']]

        df = pd.concat([heatmap1, heatmap2, heatmap3]).reset_index(drop=True).astype(
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
        summary_ovr = self.summary_ovr
        df = pd.DataFrame({'reach': list(range(0, 11)),
                           'reach_p': [1, summary_ovr['target_reach_p'][0], summary_ovr['target_reach2_p'][0],
                                       summary_ovr['target_reach3_p'][0], summary_ovr['target_reach4_p'][0],
                                       summary_ovr['target_reach5_p'][0], summary_ovr['target_reach6_p'][0],
                                       summary_ovr['target_reach7_p'][0], summary_ovr['target_reach8_p'][0],
                                       summary_ovr['target_reach9_p'][0], summary_ovr['target_reach10_p'][0]]}).astype(
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
        summary_ovr = self.summary_ovr
        trans_pop = self.trans_pop

        res = [{
            "R1_p": summary_ovr['target_reach_p'][0],
            "R3_p": summary_ovr['target_reach3_p'][0],
            "GRPs": summary_ovr['target_grps'][0],
            "AF": summary_ovr['target_af'][0],
            "R1_n": np.round(summary_ovr['target_reach_n'][0], 0),
            "R3_n": np.round(summary_ovr['target_reach3_p'][0] * trans_pop),
        }]

        j = json.loads(json.dumps(res, ensure_ascii=True))

        return (j)