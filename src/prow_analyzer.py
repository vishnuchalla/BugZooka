import os
import json
from collections import deque
from pathlib import Path
from src.xmlparser import summarize_orion_xml
from src.log_summarizer import search_prow_errors


def get_cluster_operator_errors(directory_path):
    """
    Extracts errors from the clusteroperators.json.

    :param directory_path: directory path for the artifacts
    :return: list of errors
    """
    try:
        with open(f"{directory_path}/clusteroperators.json", 'r') as f:
            cluster_operators_data = json.load(f)
        err_conditions = []
        for each_item in cluster_operators_data["items"]:
            each_dict = {"Name": each_item["metadata"]["name"]}
            for condition in each_item["status"]["conditions"]:
                if (condition["type"] == "Degraded" and condition["status"] == "True") or (condition["type"] == "Available" and condition["status"] == "False"):
                    each_dict["Status"] = condition["status"]
                    each_dict["Reason"] = condition["reason"]
                    each_dict["Message"] = condition["message"]
                    condition["status"].append(each_dict)
        return err_conditions
    except Exception as e:
        print(f"Failed to fetch log file: {e}")
        return []

def scan_orion_xmls(directory_path):
    """
    Extracts errors from orion xmls.

    :param directory_path: directory path for the artifacts
    :return: list of errors
    """
    base_dir = Path(f"{directory_path}/orion")
    xml_files = base_dir.glob("*.xml")
    for xml_file in xml_files:
        xml_content = summarize_orion_xml(xml_file)
        if  xml_content != "":
            return [xml_content]
    return []
    

def analyze_prow_artifacts(directory_path, job_name):
    """
    Analyzes prow artifacts and extracts errors.
    
    :param directory_path: directory path for the artifacts
    :param job_name: job name to base line with
    :return: list of errors
    """
    build_file_path = os.path.join(directory_path, f"build-log.txt")
    if not os.path.isfile(build_file_path):
        return ["Prow maintanence issues, couldn't even find the build-log.txt file"], False
    cluster_operators_file_path = os.path.join(directory_path, f"clusteroperators.json")
    if not os.path.isfile(cluster_operators_file_path):
        with open(build_file_path, 'r', errors='replace') as f:
            build_log_content = list(deque(f, maxlen=100))
        return ["\n Somehow couldn't find clusteroperators.json file", "\n".join(build_log_content)], False
    cluster_operator_errors = get_cluster_operator_errors(directory_path)
    if len(cluster_operator_errors) == 0:
        orion_errors = scan_orion_xmls(directory_path)
        if len(orion_errors) == 0:
            return search_prow_errors(directory_path, job_name), True
        return orion_errors, False
    return cluster_operator_errors, False
