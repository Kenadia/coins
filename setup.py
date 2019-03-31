import setuptools

with open('README.md', 'r') as f:
  long_description = f.read()

setuptools.setup(
    name='coins',
    version='0.0.1',
    author='Ken Schiller',
    author_email='kenschiller@gmail.com',
    description='Aggregate crypto balances.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Kenadia/coins',
    packages=setuptools.find_packages(),
    install_requires=[
        'coinbase==2.1.0',
        'requests',
    ],
)
