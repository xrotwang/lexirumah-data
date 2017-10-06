from setuptools import setup, find_packages


setup(
    name='pylexirumah',
    version='0.2',
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
        'clldutils>=1.12.7',
        'bibtexparser',
        'tabulate',
        'attrs',
        'cdstarcat',
    ],
    entry_points={
        'console_scripts': [
            'lexirumah=pylexirumah.cli:main',
        ]
    },
    tests_require=[],
    test_suite="pylexirumah")
