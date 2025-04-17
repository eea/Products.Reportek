pipeline {
  agent any

  environment {
        GIT_NAME = "Products.Reportek"
        GIT_SRC = "https://github.com/eea/Products.Reportek.git"
        SONARQUBE_TAGS = "bdr.eionet.europa.eu,cdr.eionet.europa.eu,cdrtest.eionet.europa.eu,cdrsandbox.eionet.europa.eu,mdr.eionet.europa.eu"
    }

 stages {

   
    stage('Cosmetics') {
      when {
        not buildingTag()
      }
      steps {
        parallel(

          "JS Hint": {
            node(label: 'docker') {
              script {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                  sh '''docker run -i --rm --name="$BUILD_TAG-jshint" -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/jshint'''
                }
              }
            }
          },

          "CSS Lint": {
            node(label: 'docker') {
              script {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                  sh '''docker run -i --rm --name="$BUILD_TAG-csslint" -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/csslint'''
                }
              }
            }
          },

          "PEP8": {
            node(label: 'docker') {
              script {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                  sh '''docker run -i --rm --name="$BUILD_TAG-pep8" -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/pep8'''
                }
              }
            }
          },

          "PyLint": {
            node(label: 'docker') {
              script {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                  sh '''docker run -i --rm --name="$BUILD_TAG-pylint" -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/pylint'''
                }
              }
            }
          }

        )
      }
    }

    stage('Code') {
      when {
        not buildingTag()
      }
      steps {
        parallel(

          "ZPT Lint": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-zptlint" -e GIT_BRANCH="$BRANCH_NAME" -e ADDONS="$GIT_NAME" -e DEVELOP="src/$GIT_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/plone-test:4 zptlint'''
            }
          },

          "JS Lint": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-jslint" -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/jslint4java'''
            }
          },

          "Flake8": {
            node(label: 'docker') {
              sh '''docker run -i --rm --pull=always --name="$BUILD_TAG-flake8"  -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/flake8 flake8 --extend-ignore=W605,W606'''
            }
          },

          "i18n": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name=$BUILD_TAG-i18n -e GIT_SRC="$GIT_SRC" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/i18ndude'''
            }
          }
        )
      }
    }

    stage('Tests') {
      when {
        not buildingTag()
      }
      steps {
        parallel(

          "Tests": {
            node(label: 'docker') {
              script {
                try {
                    sh '''docker pull eeacms/reportek-base-dr-devel; docker run -i --name="$BUILD_TAG-reportek-base-dr-devel-tests" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/reportek-base-dr-devel /debug.sh tests'''
                } finally {
                    sh '''docker rm -v $BUILD_TAG-reportek-base-dr-devel-tests'''
                }
              }
            }
          },

          "Coverage": {
            node(label: 'docker') {
              script {
                try {
                  sh '''docker pull eeacms/reportek-base-dr-devel; docker run -i --name="$BUILD_TAG-reportek-base-dr-devel-coverage" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/reportek-base-dr-devel /debug.sh coverage'''
                  sh '''mkdir -p xunit-reports; docker cp $BUILD_TAG-reportek-base-dr-devel-coverage:/opt/zope/parts/xmltestreport/testreports/. xunit-reports/'''
                  stash name: "xunit-reports", includes: "xunit-reports/*.xml"
                  sh '''docker cp $BUILD_TAG-reportek-base-dr-devel-coverage:/opt/zope/src/$GIT_NAME/coverage.xml coverage.xml'''
                  stash name: "coverage.xml", includes: "coverage.xml"
                } finally {
                  sh '''docker rm -v $BUILD_TAG-reportek-base-dr-devel-coverage'''
                }
                junit 'xunit-reports/*.xml'
              }
            }
          }
        )
      }
    }

    stage('Report to SonarQube') {
      when {
        not buildingTag()
      }
      steps {
        node(label: 'docker') {
          script{
            // get the code
            checkout scm
            // get the result of the tests that were run in a previous Jenkins test
            dir("xunit-reports") {
               unstash "xunit-reports"
             }
            // get the result of the cobertura test
             unstash "coverage.xml"
            // get the sonar-scanner binary location
            def scannerHome = tool 'SonarQubeScanner';
            // get the nodejs binary location
            def nodeJS = tool 'NodeJS11';
            // run with the SonarQube configuration of API and token
            withSonarQubeEnv('Sonarqube') {
                // make sure you have the same path to the code as in the coverage report
                 sh '''sed -i "s|/opt/zope/src/$GIT_NAME|$(pwd)|g" coverage.xml'''
                // run sonar scanner
                sh "export PATH=$PATH:${scannerHome}/bin:${nodeJS}/bin; sonar-scanner -Dsonar.python.coverage.reportPaths=coverage.xml -Dsonar.sources=./ -Dsonar.projectKey=$GIT_NAME-$BRANCH_NAME -Dsonar.projectVersion=$BRANCH_NAME-$BUILD_NUMBER"
                sh '''try=2; while [ \$try -gt 0 ]; do curl -s -XPOST -u "${SONAR_AUTH_TOKEN}:" "${SONAR_HOST_URL}api/project_tags/set?project=${GIT_NAME}-${BRANCH_NAME}&tags=${SONARQUBE_TAGS},${BRANCH_NAME}" > set_tags_result; if [ \$(grep -ic error set_tags_result ) -eq 0 ]; then try=0; else cat set_tags_result; echo "... Will retry"; sleep 60; try=\$(( \$try - 1 )); fi; done'''
            }
          }
        }
      }
    }

    stage('Pull Request') {
      when {
        not {
          environment name: 'CHANGE_ID', value: ''
        }
        environment name: 'CHANGE_TARGET', value: 'master'
      }
      steps {
        node(label: 'docker') {
          script {
            if ( env.CHANGE_BRANCH != "develop" &&  !( env.CHANGE_BRANCH.startsWith("hotfix")) ) {
                error "Pipeline aborted due to PR not made from develop or hotfix branch"
            }
           withCredentials([string(credentialsId: 'eea-jenkins-token', variable: 'GITHUB_TOKEN')]) {
            sh '''docker run -i --rm --name="$BUILD_TAG-gitflow-pr" -e GIT_CHANGE_BRANCH="$CHANGE_BRANCH" -e GIT_CHANGE_AUTHOR="$CHANGE_AUTHOR" -e GIT_CHANGE_TITLE="$CHANGE_TITLE" -e GIT_TOKEN="$GITHUB_TOKEN" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" -e GIT_ORG="$GIT_ORG" -e GIT_NAME="$GIT_NAME" eeacms/gitflow'''
           }
          }
        }
      }
    }

    stage('Release') {
      when {
        allOf {
          environment name: 'CHANGE_ID', value: ''
          branch 'master'
        }
      }
      steps {
        node(label: 'docker') {
          withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'eea-jenkins', usernameVariable: 'EGGREPO_USERNAME', passwordVariable: 'EGGREPO_PASSWORD'],string(credentialsId: 'eea-jenkins-token', variable: 'GITHUB_TOKEN'),[$class: 'UsernamePasswordMultiBinding', credentialsId: 'pypi-jenkins', usernameVariable: 'PYPI_USERNAME', passwordVariable: 'PYPI_PASSWORD']]) {
            sh '''docker pull eeacms/gitflow; docker run -i --rm --name="$BUILD_TAG-gitflow-master" -e GIT_BRANCH="$BRANCH_NAME" -e EGGREPO_USERNAME="$EGGREPO_USERNAME" -e EGGREPO_PASSWORD="$EGGREPO_PASSWORD" -e GIT_NAME="$GIT_NAME"  -e PYPI_USERNAME="$PYPI_USERNAME"  -e PYPI_PASSWORD="$PYPI_PASSWORD" -e GIT_ORG="$GIT_ORG" -e GIT_TOKEN="$GITHUB_TOKEN" eeacms/gitflow'''
          }
        }
      }
    }

  }

  post {
    always {
      script {
        def url = "${env.BUILD_URL}/display/redirect"
        def status = currentBuild.currentResult
        def subject = "${status}: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'"
        def details = """<h1>${env.JOB_NAME} - Build #${env.BUILD_NUMBER} - ${status}</h1>
                         <p>Check console output at <a href="${url}">${env.JOB_BASE_NAME} - #${env.BUILD_NUMBER}</a></p>
                      """
        emailext (subject: subject, attachLog: true, compressLog: true, to: 'eea-edw-c-team-alerts@googlegroups.com', body: details)
      }
    }
  }
}
