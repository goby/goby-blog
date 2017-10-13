pipeline {
  agent any
  stages {
    stage('Notification') {
      parallel {
        stage('build') {
          steps {
            sh 'echo "Build Step"'
            echo 'Hello World'
          }
        }
        stage('notice') {
          steps {
            echo 'Another'
          }
        }
      }
    }
    stage('style-check') {
      steps {
        echo 'Style checking'
        echo 'Style checked'
      }
    }
    stage('unit-test') {
      steps {
        echo 'testing'
      }
    }
    stage('e2e') {
      steps {
        echo 'e2e testing'
      }
    }
    stage('deploy') {
      steps {
        echo 'deploy to registry'
      }
    }
    stage('alpha-env') {
      steps {
        echo 'running on alpha-env'
      }
    }
    stage('beta-env') {
      steps {
        echo 'beta-env'
      }
    }
    stage('production') {
      steps {
        echo 'Yes!'
      }
    }
  }
}