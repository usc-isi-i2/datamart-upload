import json
import time
import logging
import os
import traceback
import datetime
from rq import get_current_job
from .store import DatamartISIUpload
from . import store


def upload_to_datamart(datamart_upload_address, dataset_information):
    logger = logging.getLogger()
    has_logger_in_stdeer = False
    for each_handler in logger.handlers:
        if "stderr" in str(each_handler.stream):
            has_logger_in_stdeer = True
    # only print once on screen
    if not has_logger_in_stdeer:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s", '%m-%d %H:%M:%S')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
    logger.setLevel(logging.DEBUG)
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s",
                        datefmt='%m-%d %H:%M:%S',
                        filename='datamart_upload_worker_{}.log'.format(os.getpid()),
                        filemode='w'
                        )

    start_time = time.time()
    job = get_current_job()
    if job is not None:
        job.meta['condition'] = "OK"
        job.meta['progress'] = "0%"
        job.meta['step'] = "Loading and processing data..."

    url = dataset_information.get("url")
    file_type = dataset_information.get("file_type")
    title = dataset_information.get("title")
    description = dataset_information.get("dataset_information")
    keywords = dataset_information.get("keywords")
    user_information = dataset_information.get("user_information")
    need_process_columns = dataset_information.get("need_process_columns")
    if not user_information:
        raise ValueError("No user information given!!!")
    wikifier_choice = dataset_information.get("wikifier_choice", "auto")
    # double check, ensure any call to upload has to be done with user verification
    upload_function_path = store.__file__
    password_record_file = os.path.join(os.path.dirname(upload_function_path), "upload_password_config.json")

    if not os.path.exists(password_record_file):
        raise ValueError("No password config file found at {}!!!".format(password_record_file))

    with open(password_record_file, "r") as f:
        user_passwd_pairs = json.load(f)

    if user_information["username"] not in user_passwd_pairs:
        raise ValueError("Given username {} does not exist!!!".format(user_information["username"]))

    try:
        datamart_upload_instance = DatamartISIUpload(update_server=datamart_upload_address,
                                                     query_server=datamart_upload_address)
        if job is not None:
            job.save_meta()
        pre_parsed_result = datamart_upload_instance.load_and_preprocess(job=job, input_dir=url, file_type=file_type,
                                                                         wikifier_choice=wikifier_choice)
        # df, meta
        if job is not None:
            job.meta['step'] = "Load and preprocess data finished..."
            job.meta['progress'] = "50%"
            job.save_meta()

        try:
            for i in range(len(pre_parsed_result.content)):
                # replace the auto-generated information to user given information if found
                if title:
                    pre_parsed_result.metadata[i]['title'] = title[i]
                if description:
                    pre_parsed_result.metadata[i]['description'] = description[i]
                if keywords:
                    pre_parsed_result.metadata[i]['keywords'] = keywords[i]
        except:
            msg = "ERROR set the user defined title / description / keywords: " + str(
                len(pre_parsed_result.metadata)) + " tables detected but only "
            if title:
                msg += str(len(title)) + " title, "
            if description:
                msg += str(len(description)) + " description, "
            if keywords:
                msg += str(len(keywords)) + "keywords"
            msg += " given."
            if job is not None:
                job.meta['condition'] = "ERROR"
                job.meta['step'] = msg
                job.save_meta()
            return

        dataset_ids = []
        upload_started_time = datetime.datetime.now()
        user_information['upload_time'] = str(upload_started_time)
        # start modeling the data
        for i in range(len(pre_parsed_result.content)):
            if job is not None:
                job.meta['step'] = "Start modeling and uploading No.{} dataset".format(str(i))
                job.meta['progress'] = str(50 + (i + 1) / len(pre_parsed_result.content) * 50) + "%"
                job.save_meta()

            if need_process_columns and len(need_process_columns) > i:
                current_need_process_columns = need_process_columns[i]
            else:
                current_need_process_columns = None
            datamart_upload_instance.model_data(inputs=pre_parsed_result,
                                                number=i, uploader_information=user_information,
                                                job=job, need_process_columns=current_need_process_columns)
            dataset_ids.append(datamart_upload_instance.modeled_data_id)
            response_id = datamart_upload_instance.upload()

        time_used = time.time() - start_time
        if job is not None:
            job.meta['step'] = "Upload finished!"
            job.meta['progress'] = "100%"
            job.meta['total time used'] = str(datetime.timedelta(seconds=time_used))
            job.meta['dataset_ids'] = dataset_ids
            job.save_meta()
        else:
            # this message will only captured when not using redis server
            msg = "Upload success! The uploaded dataset id is: {}. Upload totally used {}".format(dataset_ids, str(
                datetime.timedelta(seconds=time_used)))
            return msg

    except Exception as e:
        msg = "FAIL UPLOAD - %s \n %s" % (str(e), str(traceback.format_exc()))
        if job is not None:
            job.meta['condition'] = "ERROR"
            job.meta['step'] = msg
            job.save_meta()
        else:
            # this message will only captured when not using redis server
            return msg
