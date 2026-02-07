# pip install flask
from flask import Flask, request, jsonify, send_file
import warnings
import json
from urllib.parse import quote
from datetime import datetime, date, timedelta
import pandas as pd
from io import BytesIO
warnings.filterwarnings(action='ignore')

from CONFIG.DapData import DapData
from THEDAP_UTILS.DapUtils_v5 import DapUtils_v5

from THEDAP_SIMULATION.DapOutput_v4 import DapOutput_v4
from THEDAP_REACHCURVE.DapCurve_v4 import DapCurve_v4

from THEDAP_SIMULATION.DapOutput_v5 import DapOutput_v5
from THEDAP_REACHCURVE.DapCurve_v5 import DapCurve_v5
from THEDAP_COPULA.DapCopula import DapCopula
from THEDAP_MIXOPTIM.DapMixOptimizer import DapMixOptimizer
from THEDAP_UTILS.DapCustomModel import DapCustomModel
from THEDAP_REPORT import *

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

# 믹스 샘플 다운로드
@app.route("/mix_sample/", methods=["POST"])
def mix_sample():
    data = request.json
    userGrade = data.get("userGrade")
    userName = data.get("userName", "")

    try:
        channelVehicleList = data.get("list")
        channelVehicleDf = pd.DataFrame(channelVehicleList).groupby('platform').\
            agg(vehicle = ('product', lambda x: list(x))).reset_index()
        channelVehicleMap = {row['platform']:row['vehicle'] for _, row in channelVehicleDf.iterrows()}

        # 사용자 등급에 따른 미디어믹스 양식 파일 생성
        mix_wb = DapMixSample(channelVehicleMap, userGrade=userGrade)
        output = BytesIO()
        mix_wb.save(output)
        output.seek(0)
        
        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        reg_date = kst_now.strftime('%y%m%d') 
        filename = f"미디어믹스_샘플_({reg_date}).xlsx"
        quoted_filename = quote(filename)
        
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted_filename}"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        
        return response

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 타겟정보(target_info)
@app.route("/target_info/", methods=["POST"])
def target_info():
    data = request.json
    
    try:        
        gender = data["input_gender"]
        age_min = data["input_age_min"]
        age_max = data["input_age_max"]
        modelDate = data.get("inputModelDate", datetime.strftime(date.today(), "%Y-%m-%d"))

        thedap_utils = DapUtils_v5(inputModelDate=modelDate, pop_only=True)
        input_gender = json.dumps([{"input_gender": gender}])
        input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
        
        result = thedap_utils.get_target_info(input_gender, input_age)
        
        return result

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500
        
# 통합 Reach 분석 (reach_result)
@app.route("/reach_result/", methods=["POST"])
def reach_result():
    data = request.json
    
    try:

        mix = data["input_mix"]
        gender = data["input_gender"]
        age_min = data["input_age_min"]
        age_max = data["input_age_max"]
        weight = data["input_weight"]
        
        # 사용자 정보 & 모델버전
        userGrade = data["userGrade"]
        userName = data.get("userName", "")
        modelDate = data.get("inputModelDate", datetime.strftime(date.today(), "%Y-%m-%d"))
        
        input_mix = json.dumps(mix)
        input_gender = json.dumps([{"input_gender": gender}])
        input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
        input_weight = json.dumps([{"input_weight": weight}])
        platform_list=list(set(pd.read_json(input_mix)['platform']))
        
        # 로깅
        buf = io.StringIO()
        with redirect_stdout(buf):
            if userGrade == 'B':
                thedap_output = DapOutput_v4(
                    input_mix, input_age, input_gender, input_weight
                )
                
                summary_ = thedap_output.result_summary()
                result = {
                    "result_overall": thedap_output.result_overall(),
                    "result_summary": summary_,
                    "heatmap": thedap_output.heatmap(),
                    "reach_freq": thedap_output.reach_freq()
                }
                
            else:            
                thedap_output = DapOutput_v5(
                    input_mix, input_age, input_gender, input_weight, 
                    userName=userName, inputModelDate=modelDate,
                    platform_list=platform_list
                )
                
                summary_ = thedap_output.result_summary()
                result = {
                    "result_overall": thedap_output.result_overall(),
                    "result_summary": summary_,
                    "heatmap": thedap_output.heatmap(),
                    "reach_freq": thedap_output.reach_freq(),
                    "reach_marginal": {line['platform']:line['target_reach_p'] for line in summary_ if line['line'] == "Platform Total"},
                    "reach_union": [line['target_reach_p'] for line in summary_ if line['line'] == "Total"][0]
                }

        return jsonify({
            "status": "success",
            **result
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500 

# 분석결과 다운로드 (report_analysis)
@app.route("/report_analysis/", methods=["POST"])
def report_analysis():
    data = request.json
    userGrade = data.get("userGrade")
    reportOption = data.get("reportOption")
    
    # 사용자 등급에 따른 분석결과 엑셀 파일 생성
    try:
        if not reportOption.get("inputModelDate"):
            reportOption['inputModelDate'] = datetime.strftime(date.today(), "%Y-%m-%d")

        reportResult = data.get("reportResult")
        if reportResult.get("heatmap"):
            heatmap_re = {}
            for h in reportResult['heatmap']:
                heatmap_re[h['name']] = [
                    {
                        'e_reach_p':h['P']
                    },
                    {
                        'e_reach_n':h['N']
                    },
                    {
                        "e_grps":h['GRP']
                    }
                ]
            reportResult["heatmap"] = [heatmap_re]
            
        target_pop = data.get("target_pop")
        
        report_wb = DapReportReachAnalysis(reportOption, reportResult, target_pop, userGrade)
        output = BytesIO()
        report_wb.save(output)
        output.seek(0)
        
        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        reg_date = kst_now.strftime('%y%m%d') 
        filename = f"통합 Reach 분석결과_({reg_date}).xlsx"
        quoted_filename = quote(filename)
        
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted_filename}"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        
        return response
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 매체간 중복/도달 (reach_copula)
@app.route("/reach_copula/", methods=["POST"])
def reach_copula():
    data = request.json
    
    try:
        marginal_probs = data.get("reach_marginal")
        union_obs = data.get("reach_union")

        DC = DapCopula(marginal_probs, union_obs)
        u, i = DC.getCopulaProbs(marginal_probs, union_obs)

        result = {
            'copula_union': u,
            'copula_inter': i
        }
        
        return jsonify({
            "status": "success",
            **result
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 매체간 중복/도달 분석결과 다운로드 (report_copula)
@app.route("/report_copula/", methods=["POST"])
def report_copula():
    data = request.json
    
    reportOption = data.get("reportOption")
    reportCopula = data.get("reportCopula")
    target_pop = data.get("target_pop")
    
    try:
        
        report_wb = DapReportCopula(reportOption, reportCopula, target_pop)
        output = BytesIO()
        report_wb.save(output)
        output.seek(0)
        
        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        reg_date = kst_now.strftime('%y%m%d') 
        filename = f"매체간 중복&통합 분석결과_({reg_date}).xlsx"
        quoted_filename = quote(filename)
        
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted_filename}"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        
        return response

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 리치커브 분석 (reach_curve)
@app.route("/reach_curve/", methods=["POST"])
def reach_curve():
    data = request.json
    
    try:

        mix = data["input_mix"]
        gender = data["input_gender"]
        age_min = data["input_age_min"]
        age_max = data["input_age_max"]
        weight = data["input_weight"]
        maxbudget = data["input_maxbudget"]
        seq = data["input_seq"]

        # 사용자 정보 & 모델버전
        userGrade = data["userGrade"]
        userName = data.get("userName", "")
        modelDate = data.get("inputModelDate", datetime.strftime(date.today(), "%Y-%m-%d"))

        input_mix = json.dumps(mix)
        input_gender = json.dumps([{"input_gender": gender}])
        input_age = json.dumps([{"input_age_min": age_min, "input_age_max":age_max}])
        input_weight = json.dumps([{"input_weight": weight}])
        input_maxbudget = json.dumps([{"input_maxbudget": maxbudget}])
        input_seq = json.dumps([{"input_seq": seq}])
        platform_list=list(set(pd.read_json(input_mix)['platform']))
        
        if userGrade == 'B':
            rc = DapCurve_v4()
        else:
            rc = DapCurve_v5(
                userName=userName, inputModelDate=modelDate, 
                platform_list=platform_list
            )

        result = rc.reach_curve(input_mix, input_age, input_gender, input_weight, input_seq, input_maxbudget)
        
        return jsonify({
            "status":"success",
            **result
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 리치커브 분석결과 다운로드 (report_curve)
@app.route("/report_curve/", methods=["POST"])
def report_curve():
    data = request.json
    reportOption = data.get("reportOption")
    reportCurve = data.get("reportCurve")
    target_pop = data.get("target_pop")
    
    try:
        report_wb = DapReportReachCurve(reportOption, reportCurve, target_pop)
        output = BytesIO()
        report_wb.save(output)
        output.seek(0)
        
        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        reg_date = kst_now.strftime('%y%m%d') 
        filename = f"리치커브 분석결과_({reg_date}).xlsx"
        quoted_filename = quote(filename)
        
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted_filename}"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"

        return  response
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 미디어믹스 최적화 (reach_optimize)
@app.route("/reach_optimize/", methods=["POST"])
def reach_optimize():
    data = request.json
    
    type = data.get("opt_type")
    # 사용자 정보 & 모델버전
    userName = data.get("userName", "")
    modelDate = data.get("inputModelDate", datetime.strftime(date.today(), "%Y-%m-%d"))
    
    try:
        # REACH MAX
        if type == "reach_max":
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
            platform_list = list(set(pd.read_json(opt_mix)['platform']))

            optimizer = DapMixOptimizer(
                opt_type=opt_type,
                opt_mix=opt_mix,
                input_age=input_age,
                input_gender=input_gender,
                input_weight=input_weight,
                opt_maxbudget=opt_maxbudget,
                opt_seq=opt_seq,
                userName=userName,
                inputModelDate=modelDate,
                platform_list=platform_list
            )

            result = optimizer.get_result()

        # REACH TARGET
        elif type == "reach_target":
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
            platform_list = list(set(pd.read_json(opt_mix)['platform']))
            
            checker = DapUtils_v5()
            chkFlag = checker.check_coverage(opt_mix, opt_target, input_age, input_gender)
            if chkFlag :
                optimizer = DapMixOptimizer(
                    opt_type=opt_type,
                    opt_mix=opt_mix,
                    input_age=input_age,
                    input_gender=input_gender,
                    input_weight=input_weight,
                    opt_target=opt_target,
                    userName=userName,
                    inputModelDate=modelDate,
                    platform_list=platform_list
                )

                result = optimizer.get_result()
                result['isSuc'] = True
            else:
                result = {"isSuc":False}
        
        elif type == "reach_spectrum":
            mixA = data["input_mixA"]
            mixB = data["input_mixB"]
            age_min = data["input_age_min"]
            age_max = data["input_age_max"]
            gender = data["input_gender"]
            weight = data["input_weight"]
            maxbudget = data["opt_maxbudget"]
            seq = data["opt_seq"]
            
            opt_type = json.dumps([{"opt_type": type}])
            opt_mix = [{"mix_a": mixA, "mix_b": mixB}]
            input_age = json.dumps([{"input_age_min": age_min, "input_age_max": age_max}])
            input_gender = json.dumps([{"input_gender": gender}])
            input_weight = json.dumps([{"input_weight": weight}])
            opt_maxbudget = json.dumps([{"opt_maxbudget": maxbudget}])
            opt_seq = json.dumps([{"opt_seq": seq}])
            platform_list = list(set([l['platform'] for l in mixA] + [l['platform'] for l in mixB]))

            optimizer = DapMixOptimizer(
                opt_type=opt_type,
                opt_mix=opt_mix,
                input_age=input_age,
                input_gender=input_gender,
                input_weight=input_weight,
                opt_maxbudget=opt_maxbudget,
                opt_seq=opt_seq,
                userName=userName,
                inputModelDate=modelDate,
                platform_list=platform_list
            )

            result = optimizer.get_result()
        
        else:
            return jsonify({
                "status": "error", 
                "message": "Invalid opt_type"
            }), 400
        
        return jsonify({
            "status": "success",
            **result
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 미디어믹스 최적화 분석결과 다운르도 (report_optimize)
@app.route("report_optimize/", methods=["POST"])
def report_optimize():
    data = request.json
    
    try:
        reportOption = data.get("reportOption")
        opt_type = reportOption.get('opt_type')

        reportOptimize = data.get("reportOptimize")
        target_pop = data.get("target_pop")
        
        if opt_type in ['reach_max', 'target_reach']:
            
            report_wb = DapReportReachOptimize(
                reportOption=reportOption,
                reportOptimize=reportOptimize,
                target_pop=target_pop
            )
        
        else:
            report_wb = DapReportReachSpectrum(
                reportOption=reportOption,
                reportOptimize=reportOptimize,
                target_pop=target_pop
            )
        
        output = BytesIO()
        report_wb.save(output)
        output.seek(0)
        opt_type_kr = '도달 극대화' if opt_type == "reach_max" else \
            ('도달률 달성' if opt_type == "reach_target" else \
            "도달 스펙트럼")

        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        reg_date = kst_now.strftime('%y%m%d') 
        filename = f"{opt_type_kr} 분석결과_({reg_date}).xlsx"
        quoted_filename = quote(filename)
            
        response = send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted_filename}"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"

        return response 
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500     

# 모델 커스텀
@app.route("/reach_custom/", methods=["POST"])
def reach_custom():
    data = request.json

    uploadData = data.get('uploadData')
    if not uploadData:
        return jsonify({
            "status": "fail",
            "message": "NoDataError"
        }), 400

    DCM = DapCustomModel(uploadData=uploadData)
    
    # 전달받은 데이터의 행 수가 20 미만일 때 -> RowNumError
    if len(DCM.uploadData) < 20:
        return jsonify({
            "status": "fail",
            "message": f"RowNumError", 
        }), 422 
	
    # 분석 성공
    try:
        result = DCM.getResult()
        return jsonify({
            "status": "success",
            "message": "Complete",
            **result
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"{str(e)}"
        }), 500

# 매체, 상품 조회 (get_media_product)
@app.route("/get_media_product/", methods=["GET"])
def get_media_product():
    obj_ = DapData()
    result = obj_.getMediaProduct()
    result_json = result.to_json(orient="records")
    return result_json


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8200)
