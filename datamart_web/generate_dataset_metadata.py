from datamart_isi import config as config_datamart

dataset_paths = ["/data",  # for docker
                 "/nfs1/dsbox-repo/data/datasets/seed_datasets_data_augmentation",  # for dsbox server
                 "/nfs1/dsbox-repo/data/datasets/seed_datasets_current",  # for dsbox server
                 "/Users/minazuki/Desktop/studies/master/2018Summer/data/datasets/seed_datasets_data_augmentation"
                 ]

def generate_dataset_metadata():
    '''
    Add D3M dataset metadata to cache
    '''
    print('Running generate_dataset_metadata')
    from datamart_isi.cache import metadata_cache
    import os
    import pathlib

    memcache_dir = pathlib.Path(config_datamart.cache_file_storage_base_loc) / 'datasets_cache'
    if not memcache_dir.exists():
        os.makedirs(memcache_dir)

    for path in dataset_paths:
        path = pathlib.Path(path)
        if path.exists:
            metadata_cache.MetadataCache.generate_real_metadata_files([str(path)])
    print('Done generate_dataset_metadata')


if __name__ == '__main__':
    generate_dataset_metadata()
