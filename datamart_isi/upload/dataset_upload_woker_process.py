
import time
import logging
import os
import traceback
import datetime
from rq import get_current_job
from datamart_isi.upload.store import Datamart_isi_upload
from datamart_isi.upload import store


def upload_to_datamart(datamart_upload_address, dataset_information):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s",
                        datefmt='%m-%d %H:%M:%S',
                        filename='datamart_upload_worker_{}.log'.format(os.getpid()),
                        filemode='w'
                        )
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s", '%m-%d %H:%M:%S')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    start_time = time.time()
    job = get_current_job()
    job.meta['condition'] = "OK"
    job.meta['progress'] = "0%"
    job.meta['step'] = "Loading and processing data..."

    url = dataset_information.get("url")
    file_type = dataset_information.get("file_type")
    title = dataset_information.get("title")
    description = dataset_information.get("dataset_information")
    keywords = dataset_information.get("keywords")
    user_information = dataset_information.get("user_information")
    if not user_information:
        raise ValueError("No user information given!!!")
    wikifier_choice = dataset_information.get("wikifier_choice", "auto")
    # double check, ensure any call to upload has to be done with user verification
    upload_function_path = store.__file__
    password_record_file = os.path.join(os.path.dirname(upload_function_path), "upload_password_config.json")

    if not os.path.exists(password_record_file):
        raise ValueError("No password config file found at {}!!!".format(password_record_file))

    with open(password_record_file ,"r") as f:
        user_passwd_pairs = json.load(f)

    if user_information["username"] not in user_passwd_pairs:
        raise ValueError("Given username {} does not exist!!!".format(user_information["username"]))

    try:
        datamart_upload_instance = Datamart_isi_upload(update_server=datamart_upload_address,
                                                       query_server=datamart_upload_address)
        job.save_meta()
        df, meta = datamart_upload_instance.load_and_preprocess(job=job, input_dir=url, file_type=file_type, wikifier_choice=wikifier_choice)
        job.meta['step'] = "Load and preprocess data finished..."
        job.meta['progress'] = "50%"
        job.save_meta()
        try:
            for i in range(len(df)):
                if title:
                    meta[i]['title'] = title[i]
                if description:
                    meta[i]['description'] = description[i]
                if keywords:
                    meta[i]['keywords'] = keywords[i]
        except:
            msg = "ERROR set the user defined title / description / keywords: " + str(
                len(meta)) + " tables detected but only "
            if title:
                msg += str(len(title)) + " title, "
            if description:
                msg += str(len(description)) + " description, "
            if keywords:
                msg += str(len(keywords)) + "keywords"
            msg += " given."
            job.meta['condition'] = "ERROR"
            job.meta['step'] = msg
            job.save_meta()
            return

        dataset_ids = []
        upload_started_time = datetime.datetime.now()
        user_information['upload_time'] = str(upload_started_time)
        for i in range(len(df)):
            job.meta['step'] = "Start modeling and uploading No.{} dataset".format(str(i))
            job.meta['progress'] = str(50 + (i+1) / len(df) * 50) + "%"
            job.save_meta()
            datamart_upload_instance.model_data(input_dfs=df, metadata=meta, number=i, uploader_information=user_information, job=job)
            dataset_ids.append(datamart_upload_instance.modeled_data_id)
            response_id = datamart_upload_instance.upload()

        time_used = time.time() - start_time
        job.meta['step'] = "Upload finished!"
        job.meta['progress'] = "100%"
        job.meta['total time used'] = str(datetime.timedelta(seconds=time_used))
        job.meta['dataset_ids'] = dataset_ids
        job.save_meta()

    except Exception as e:
        msg="FAIL UPLOAD - %s \n %s" % (str(e), str(traceback.format_exc()))
        job.meta['condition'] = "ERROR"
        job.meta['step'] = msg
        job.save_meta() 

    finally:
        return