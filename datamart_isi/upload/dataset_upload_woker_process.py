
import time
import logging
from rq import get_current_job
from datamart_isi.upload.store import Datamart_isi_upload


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.DEBUG)
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s %(lineno)d -- %(message)s",
                    datefmt='%m-%d %H:%M:%S',
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


def upload_to_datamart(url, file_type, datamart_upload_address, title=None, description=None, keywords=None):
    start_time = time.time()
    job = get_current_job()
    job.meta['condition'] = "OK"
    job.meta['progress'] = "0%"
    job.meta['step'] = "Loading and processing data..."
    try:
        datamart_upload_instance = Datamart_isi_upload(update_server=datamart_upload_address,
                                                       query_server=datamart_upload_address)
        job.save_meta()
        df, meta = datamart_upload_instance.load_and_preprocess(job=job, input_dir=url, file_type=file_type)
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

        for i in range(len(df)):
            job.meta['step'] = "Start modeling and uploading No.{} dataset".format(str(i))
            job.meta['progress'] = str(50 + len(df) / i * 50) + "%"
            job.save_meta()
            datamart_upload_instance.model_data(df, meta, i)
            response_id = datamart_upload_instance.upload()
        time_used = time.time() - start_time
        job.meta['step'] = "Upload finished!"
        job.meta['progress'] = "100%"
        job.meta['total time used'] = str(datetime.timedelta(seconds=time_used))
        job.save_meta()

    except Exception as e:
        msg="FAIL UPLOAD - %s \n %s" % (str(e), str(traceback.format_exc()))
        job.meta['condition'] = "ERROR"
        job.meta['step'] = msg
        job.save_meta() 

    finally:
        return