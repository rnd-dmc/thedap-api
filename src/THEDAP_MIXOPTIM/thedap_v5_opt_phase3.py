import pandas as pd
import numpy as np

from THEDAP_MIXOPTIM.thedap_v5_opt_phase2 import getOPTPhase2


class getOPTPhase3(getOPTPhase2):
    
    def __init__(self):
        super().__init__()

    def opt_phase3(self, opt_mix, input_age, input_gender, input_weight, opt_target, start_point=1.0, margin=.01):
        opt_mix_cleaned = self.opt_tidy(opt_mix, input_age, input_gender)
        target_reach = pd.read_json(opt_target).iloc[0, 0]
        seq_ = "[{\"opt_seq\": \"1\"}]"
        ucl, lcl = target_reach + margin, target_reach - margin

        ind = 0
        budget_list, op2_list, fr2_list, res_vals, mpe_list = [], [], [], [], []
        
        learning_rate = 1.2
        direction_ = 1.0

        while True:
            if ind == 0:
                budget_ = target_reach * 100 
            else:
                momentum = np.sqrt(ind + 1) 
                step = mpe_list[-1] * direction_ * momentum * learning_rate
                
                # 도달률이 정체될 때(mpe 변화가 적을 때) 강제로 보폭을 확보
                if ind > 5 and abs(res_vals[-1] - res_vals[-2]) < 0.001:
                    step *= 1.5 
                
                step = np.clip(step, -0.4, 2.0)
                budget_ = budget_list[-1] * (1 + step)

            budget_ = max(start_point, budget_)
            budget_list.append(np.round(budget_, 6))

            maxbudget_ = f'[{{\"opt_maxbudget\": \"{budget_list[ind]}\"}}]'
            current_ftol = 1e-03 if ind < 10 else 1e-04 
                
            op2_, fr2_ = self.opt_phase2(opt_mix=opt_mix, input_age=input_age, input_gender=input_gender, 
                                         input_weight=input_weight, opt_seq=seq_, opt_maxbudget=maxbudget_, 
                                         ftol=current_ftol)
            
            res_val_ = np.max(op2_[0]['target_reach_p'])
            op2_list.append(op2_[0]); fr2_list.append(fr2_); res_vals.append(res_val_)
            
            mpe_ = np.abs(target_reach - res_val_) / target_reach
            mpe_list.append(mpe_)
            
            print(res_val_)
            # 방향 전환 시 감쇠
            if res_val_ > target_reach:
                if direction_ == 1.0: learning_rate *= 0.6
                direction_ = -1.0
            else:
                if direction_ == -1.0: learning_rate *= 0.6
                direction_ = 1.0

            ind += 1
            if (res_val_ >= lcl) and (res_val_ <= ucl):
                if res_val_ >= target_reach: break
            if ind >= 20: break
        
        idx = np.argmin([abs(target_reach - v) for v in res_vals])
        return [[op2_list[idx]], fr2_list[idx]]