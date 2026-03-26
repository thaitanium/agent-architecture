from setuptools import setup, find_packages
setup(
    name="agent-architecture",
    version="1.0.0",
    description="Multi-agent system for AI-powered app development using Claude 4.6",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/thaitanium/agent-architecture",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "anthropic>=0.28.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
)
