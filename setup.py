from setuptools import setup, find_packages


setup(
    name='pylexirumah',
    version='0.3',
    description='programmatic access to lexirumah-data',
    long_description='',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
    ],
    author='Gereon A. Kaiping',
    author_email='g.a.kaiping@hum.leidenuniv.nl',
    url='',
    keywords='data linguistics',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pycldf',
        'clldutils',
        'newick',
        'geopy',
        'xlrd', # For importing from Excel files
        'lexirumah',
	'numpy',
	'pyclts',
	'segments',
    ],
    entry_points={
        'lexibank.dataset': [
            'lexirumah=pylexirumah.lexibank:Dataset',
        ],
        'console_scripts': [
            'segment=pylexirumah.segment:main',
        ]
    },
    tests_require=[],
    test_suite="pylexirumah")
