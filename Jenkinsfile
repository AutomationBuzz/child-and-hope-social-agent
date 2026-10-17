pipeline {
  agent any
  options {
    timestamps()
    ansiColor('xterm')
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '20'))
  }
  parameters {
    booleanParam(name: 'GENERATE_RESEARCH_DRAFTS', defaultValue: true, description: 'Run research and creative agents automatically')
  }
  triggers {
    cron('H 14 * * 1,5')
  }
  environment {
    PYTHONUNBUFFERED = '1'
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Python environment') {
      steps {
        sh '''
          python3 --version
          python3 -m venv .venv
          . .venv/bin/activate
          python -m pip install --upgrade pip
          pip install -r requirements.txt PyYAML
        '''
      }
    }
    stage('Static validation') {
      steps {
        sh '''
          . .venv/bin/activate
          python -m compileall -q src
          python - <<'PY'
import json
from pathlib import Path
import yaml

for p in sorted(Path("data").glob("*.json")):
    json.loads(p.read_text(encoding="utf-8"))
    print(f"Valid JSON: {p}")

workflow_paths = sorted(Path(".github/workflows").glob("*.yml")) + sorted(Path(".github/workflows").glob("*.yaml"))
for p in workflow_paths:
    with p.open(encoding="utf-8") as f:
        yaml.safe_load(f)
    print(f"Valid workflow YAML: {p}")

history = Path("data/research_history.json")
if history.exists():
    data = json.loads(history.read_text(encoding="utf-8"))
    if not isinstance(data.get("used_studies"), list):
        raise SystemExit("research_history.json must contain a used_studies list")
print("Repository validation passed")
PY
          if [ -d tests ]; then python -m pytest -q tests; else echo "No tests/ directory; syntax and config validation completed."; fi
        '''
      }
    }
    stage('Research draft generation') {
      when { expression { return params.GENERATE_RESEARCH_DRAFTS } }
      steps {
        retry(2) {
          sh '''
            . .venv/bin/activate
            python src/research_poster_agent.py
            python src/research_reel_agent.py
          '''
        }
      }
      post {
        always {
          archiveArtifacts artifacts: 'artifacts/**', allowEmptyArchive: true, fingerprint: true
          archiveArtifacts artifacts: '*review_report.md,*caption*.txt,*summary.md,*storyboard.json', allowEmptyArchive: true, fingerprint: true
        }
      }
    }
  }
  post {
    success {
      echo 'CHILD & HOPE pipeline passed. Research/creative agents ran when enabled; Facebook publishing remains disabled until its idempotency and end-to-end verification gates are implemented.'
    }
    failure {
      echo 'Pipeline failed. Preserve logs and artifacts for diagnosis. Only retry safe draft-generation operations; never blindly retry a Facebook publish request.'
    }
    always {
      cleanWs(deleteDirs: true, notFailBuild: true)
    }
  }
}
