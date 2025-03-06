from setuptools import setup, find_packages

setup(
    name="hls_analysis",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.1",
    ],
    entry_points={
        'console_scripts': [
            'analyze-hls=src.analyze_hls:main',
        ],
    },
    python_requires='>=3.6',
    author="Justin Crisafulli",
    description="A tool to analyze HLS (HTTP Live Streaming) playlists",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Crisafulli-2/hls_analysis_ffmpeg",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
