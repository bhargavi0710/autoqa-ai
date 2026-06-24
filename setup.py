from setuptools import find_packages, setup

setup(
    name="autoqa-ai",
    version="1.0.0",
    description="AI-powered automated QA testing tool",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "autoqa=main:main",
        ],
    },
)
