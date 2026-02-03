# pip install flask
from flask import Flask, request
import warnings
import json
warnings.filterwarnings(action='ignore')

from CONFIG.thedap_db import getDATA
from THEDAP_UTILS.thedap_v5_utils import getUTIL_v5

from THEDAP_SIMULATION.thedap_v4_output import THEDAP_OUTPUT_v4
from THEDAP_REACHCURVE.thedap_v4_reachcurve import getCurve_v4

from THEDAP_SIMULATION.thedap_v5_output import THEDAP_OUTPUT_v5
from THEDAP_REACHCURVE.thedap_v5_reachcurve import getCurve_v5

from THEDAP_MIXOPTIM.thedap_v5_mixoptim import OPTIM_OUTPUT

# import CONFIG.thedap_db as db

##### 로깅
import logging
from contextlib import redirect_stdout
import io
import sys
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    stream=sys.stdout,  
)
logger = logging.getLogger("reach.api")

class PrintLogger:
    def write(self, msg):
        msg = msg.strip()
        if msg:
            logger.info(msg)
    def flush(self):
        pass

sys.stdout = PrintLogger()
sys.stderr = PrintLogger() 
#####


app = Flask(__name__)

# 타겟정보
@app.route("/target_info/", methods=["POST"])
def target_info():
    data = request.json
    gender = data["input_gender"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]

    obj_ = getUTIL_v5()
    # thedap_v4.py 파라미터 정보에 맞춰 변경
    input_gender = json.dumps([{"input_gender": gender}])
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
    
    result = obj_.get_target_info(input_gender, input_age)
    return result


# 결과계산
@app.route("/result_summary/", methods=["POST"])
def result_summary():
    data = request.json

    mix = data["input_mix"]
    gender = data["input_gender"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    weight = data["input_weight"]
    userGrade = data["userGrade"]
    
    # thedap_v4_output.py 파라미터 정보에 맞춰 변경
    input_mix = json.dumps(mix)
    input_gender = json.dumps([{"input_gender": gender}])
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
    input_weight = json.dumps([{"input_weight": weight}])
    
    # 로깅
    buf = io.StringIO()
    with redirect_stdout(buf):
        if userGrade == 'B':
            thedap_output = THEDAP_OUTPUT_v4(input_mix, input_age, input_gender, input_weight)
        else:
            thedap_output = THEDAP_OUTPUT_v5(input_mix, input_age, input_gender, input_weight)

        result = thedap_output.result_summary()

    return result

# 히트맵
@app.route("/heatmap/", methods=["POST"])
def heatmap():
    data = request.json

    mix = data["input_mix"]
    gender = data["input_gender"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    weight = data["input_weight"]
    userGrade = data["userGrade"]

    # thedap_v4_output.py 파라미터 정보에 맞춰 변경
    input_mix = json.dumps(mix)
    input_gender = json.dumps([{"input_gender": gender}])
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
    input_weight = json.dumps([{"input_weight": weight}])

    if userGrade == 'B':
        thedap_output = THEDAP_OUTPUT_v4(input_mix, input_age, input_gender, input_weight)
    else:
        thedap_output = THEDAP_OUTPUT_v5(input_mix, input_age, input_gender, input_weight)

    
    result = thedap_output.heatmap()
    return result


# 도달 빈도분포 (reach_freq)
@app.route("/reach_freq/", methods=["POST"])
def reach_freq():
    data = request.json

    mix = data["input_mix"]
    gender = data["input_gender"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    weight = data["input_weight"]
    userGrade = data["userGrade"]

    # thedap_v4_output.py 파라미터 정보에 맞춰 변경
    input_mix = json.dumps(mix)
    input_gender = json.dumps([{"input_gender": gender}])
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
    input_weight = json.dumps([{"input_weight": weight}])

    if userGrade == 'B':
        thedap_output = THEDAP_OUTPUT_v4(input_mix, input_age, input_gender, input_weight)
    else:
        thedap_output = THEDAP_OUTPUT_v5(input_mix, input_age, input_gender, input_weight)


    result = thedap_output.reach_freq()
    return result


# 분석결과 요약 (result_overall)
@app.route("/result_overall/", methods=["POST"])
def result_overall():
    data = request.json

    mix = data["input_mix"]
    gender = data["input_gender"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    weight = data["input_weight"]
    userGrade = data["userGrade"]

    # thedap_v4_output.py 파라미터 정보에 맞춰 변경
    input_mix = json.dumps(mix)
    input_gender = json.dumps([{"input_gender": gender}])
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
    input_weight = json.dumps([{"input_weight": weight}])

    if userGrade == 'B':
        thedap_output = THEDAP_OUTPUT_v4(input_mix, input_age, input_gender, input_weight)
    else :
        thedap_output = THEDAP_OUTPUT_v5(input_mix, input_age, input_gender, input_weight)
    
    result = thedap_output.result_overall()
    return result


# 리치커버 분석 (reach_curve)
@app.route("/reach_curve/", methods=["POST"])
def reach_curve():
    data = request.json

    mix = data["input_mix"]
    gender = data["input_gender"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    weight = data["input_weight"]
    maxbudget = data["input_maxbudget"]
    seq = data["input_seq"]
    userGrade = data["userGrade"]

    # thedap_v4_output.py 파라미터 정보에 맞춰 변경
    input_mix = json.dumps(mix)
    input_gender = json.dumps([{"input_gender": gender}])
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
    input_weight = json.dumps([{"input_weight": weight}])
    input_maxbudget = json.dumps([{"input_maxbudget": maxbudget}])
    input_seq = json.dumps([{"input_seq": seq}])

    if userGrade == 'B':
        rc = getCurve_v4()
    else:
        rc = getCurve_v5()

    result = rc.reach_curve(input_mix, input_age, input_gender, input_weight, input_seq, input_maxbudget)
    
    return result


# 분석결과 요약 (result_overall)

@app.route("/reach_max/", methods=["POST"])
def reach_max():
    data = request.json

    type = data["opt_type"]
    mix = data["input_mix"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    gender = data["input_gender"]
    weight = data["input_weight"]
    maxbudget = data["opt_maxbudget"]
    seq = data["opt_seq"]

    opt_type = json.dumps([{"opt_type": type}])
    opt_mix = json.dumps(mix)
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max": age_max}])
    input_gender = json.dumps([{"input_gender": gender}])
    input_weight = json.dumps([{"input_weight": weight}])
    opt_maxbudget = json.dumps([{"opt_maxbudget": maxbudget}])
    opt_seq = json.dumps([{"opt_seq": seq}])

    thedap_output = OPTIM_OUTPUT(
        opt_type,
        opt_mix,
        input_age,
        input_gender,
        input_weight,
        opt_seq=opt_seq,
        opt_maxbudget=opt_maxbudget
    )

    result = thedap_output.get_result()
    return result

@app.route("/reach_target/", methods=["POST"])
def reach_target():
    data = request.json

    type = data["opt_type"]
    mix = data["input_mix"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    gender = data["input_gender"]
    weight = data["input_weight"]
    target = data["opt_target"]

    opt_type = json.dumps([{"opt_type": type}])
    opt_mix = json.dumps(mix)
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max": age_max}])
    input_gender = json.dumps([{"input_gender": gender}])
    input_weight = json.dumps([{"input_weight": weight}])
    opt_target = json.dumps([{"opt_target": target}])

    checker = getUTIL_v5()
    chkFlag = checker.check_coverage(opt_mix, opt_target, input_age, input_gender)
    if chkFlag :

        thedap_output = OPTIM_OUTPUT(
            opt_type,
            opt_mix,
            input_age,
            input_gender,
            input_weight,
            opt_target=opt_target,
        )

        result = thedap_output.get_result()
        result['isSuc'] = True
    else:
        result = {"isSuc":False}



    return result

@app.route("/reach_spectrum/", methods=["POST"])
def reach_spectrum():
    data = request.json

    type = data["opt_type"]
    mixA = data["input_mixA"]
    mixB = data["input_mixB"]
    age_min = data["input_age_min"]
    age_max = data["input_age_max"]
    gender = data["input_gender"]
    weight = data["input_weight"]
    maxbudget = data["opt_maxbudget"]
    seq = data["opt_seq"]

    opt_type = json.dumps([{"opt_type": type}])
    opt_mix = json.loads(json.dumps([{"mix_a": mixA, "mix_b":mixB}]))
    input_age = json.dumps([{"input_age_min": age_min, "input_age_max": age_max}])
    input_gender = json.dumps([{"input_gender": gender}])
    input_weight = json.dumps([{"input_weight": weight}])
    opt_maxbudget = json.dumps([{"opt_maxbudget": maxbudget}])
    opt_seq = json.dumps([{"opt_seq": seq}])

    thedap_output = OPTIM_OUTPUT(
        opt_type,
        opt_mix,
        input_age,
        input_gender,
        input_weight,
        opt_maxbudget=opt_maxbudget,
        opt_seq=opt_seq
    )

    result = thedap_output.get_result()
    return result



# 매체, 상품 조회 (get_media_product)
@app.route("/get_media_product/", methods=["GET"])
def get_media_product():
    obj_ = getDATA()
    result = obj_.getMediaProduct()
    result_json = result.to_json(orient="records")
    return result_json


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8200)
