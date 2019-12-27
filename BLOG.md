## Infrastructure as Code with AWS: Lambda and API Gateway

Defining infrastructure as code allows the foundation of a system to be repeatable, consistent, version controlled, human readable, centralized and composable. This tutorial will walk through creating a Rest API in AWS using APIGateway and Lambda, managed with CloudFormation.

> <strong>Infrastructure as code</strong> is the management of cloud resources via descriptive machine readable templates that act as instructions on how to create and provision the necessary building blocks of a computational system.
>
> \- AWS

##### This tutorial demonstrates:
1. The basics of CloudFormation
1. How to work with the AWS CLI
1. Creating IAM roles
1. Creating a Python Lambda function
1. Creating a rest API with APIGateway

#### Table of Contents

1. [**Introduction**](#introduction)
    - [CloudFormation Template](#cloudformationtemplate)
    - [Intrinsic Functions](#intrinsicfunctions)
    - [AWS CLI Setup](#awsclisetup)
1. [**Basic Lambda Code**](#lambdacode)
    - [Lambda IAM role](#createlambdaiamrole)
    - [Lambda Function](#lambdafunction)
    - [Zip It](#zipit)
    - [Test Lambda Code](#testlambdacode)
    - [Upload to S3](#uploadcodetos3bucket)
1. [**Lambda and APIGateway in CloudFormation**](#lambdaandapigatewayincloudformation)
    - [Lambda](#lambdaincloudformation)
    - [APIGateway](#apigateway)
        - [Role](#apigatewayrole)
        - [Rest API](#restapi)
        - [Method](#method)
        - [Deployment](#deployment)
        - [Stage](#stage)
1. [**Deploy and Test**](#deployandtest)
1. [**Consolidate**](#consolidate)
    - [Use Parameters](#useparameters)
    - [Use Outputs](#useoutputs)

## Introduction

This is a diagram of what will be accomplished by the end of the tutorial:

![Flow Chart](https://blog.petej.org/content/images/2019/12/tutorial_flow_chart.png)

<a href="https://github.com/topleft/boomer-api" target="_blank">Finished code in github.</a>

#### CloudFormation Template

> [AWS CloudFormation Docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)


CloudFormation templates are extremely flexible and extensible. Much of the AWS ecosystem can be instrumented via CloudFormation and it can be overwhelming when investigating for the first time. To simplify things, understand that there only five top level elements in CloudFormation templates and everything that is written in a template will fit within one of these keys.

5 Top level CloudFormation keys:

```
{
  "AWSTemplateFormatVersion": "",
  "Description": "",
  "Parameters": {},
  "Resources": {},
  "Outputs": {}
}
```

- **Required Keys**:
    - **AWSTemplateFormatVersion** - determines the version syntax/structure for the CloudFormation template
    - **Resources** - defines the object(s) within AWS that you are creating

- **Optional Keys**:
    - **Description** - a human readable string describing you stack
    - **Parameters** - variables to use within the template
    - **Outputs** - variables that can be accessed from other templates

The **Resources** object is where most of the magic happens when writing CF templates. There are a [couple hundred resource types](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) and each one has a different set of keys and values to specify how it will be configured. This tutorial will utilize six _Resource Types_:

1. `AWS::IAM::Role`
1. `AWS::Lambda::Function`
1. `AWS::ApiGateway::RestApi`
1. `AWS::ApiGateway::Method`
1. `AWS::ApiGateway::Stage`
1. `AWS::ApiGateway::Deployment`

#### Intrinsic Functions

There are many [functions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html) that can be used inside of CF templates to help with attribute access, concatenation, substitution, variable reference and more. These functions main objective is to make templates more reusable and maintainable by allowing variables and references. The function syntax itself can look a bit cryptic, but given a second look it can be seen that they are generally performing very simple tasks.

#### AWS CLI Setup

This tutorial utilizes the AWS CLI for 100% of the interaction with AWS. Feel free to use the UI, but be sure to set up the CLI locally as well so that you can more easily follow along.

>Do you have the AWS CLI installed ... not sure? Run:
>
>```sh
>$ aws  --version
>```
>
>If your terminal outputs ... 'command not found' or something similar then you'll need to install it: [click here for instructions](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html).

>Do you have your AWS credentials setup locally?
>```sh
>$ aws s3 ls
>```
> If you receive an 'access denied' response then you will need to setup your AWS credentials.
>Start with  the [Quick Instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration) to get understand how this configuration works. Once that is comfortable, I would recommend setting up [Named Profiles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html).

Note that if you setup **Named Profiles** for your AWS credentials and _did not specify a `[default]`_ then you will need to add `--profile yourProfile` to all of these commands.

## Lambda Code

At this point in the tutorial, the local environment has been setup and some CloudFormation basics have been introduced. Now coding begins and the project starts to  to take its shape with the initial Lambda implementation.

#### Project Setup

Structure:
```
├── cloudformation
│   ├── resources.json
│   └── roles.json
├── function.py
└── readme.md
```

#### Create Lambda IAM Role

AWS IAM Roles are reusable collections of policies that are assigned to resources in AWS. A policy is an object in AWS that, when associated with an identity or resource, defines their permissions. In other words, roles and policies are define _what_ and _who_. When associated with resources they control _what_ a resource can do and _who_ that resource can do it with.

> [Amazon IAM Documentation](https://docs.aws.amazon.com/iam/?id=docs_gateway)

By default, AWS Lambda requires access to create logs in AWS's logging solution,  [Cloudwatch](https://aws.amazon.com/cloudwatch/). This minimum access consists of three permissions: _logs:CreateLogGroup_,  _logs:CreateLogStream_, _logs:PutLogEvents_. As well to create a lambda via CloudFormation the function code needs to exist in an S3 bucket, so the Lambda will also need access to that S3 bucket via the _s3:GetObject_ permission. In this case that bucket is called _pj-lambda-functions_.

Add the following lines to the _cloudformation/roles.json_:

```
{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "LambdaRole": {
      "Type": "AWS::IAM::Role",
      "Properties": {
        "RoleName": "pj-basic-lambda",
        "AssumeRolePolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {
              "Service": ["lambda.amazonaws.com"]
            },
            "Action": ["sts:AssumeRole"]
          }]
        },
        "Path": "/",
        "Policies": [{
            "PolicyName": "AWSLambdaBasicExecutionRole",
            "PolicyDocument": {
              "Version": "2012-10-17",
              "Statement": [{
                "Effect": "Allow",
                "Action": [
                  "logs:CreateLogGroup",
                  "logs:CreateLogStream",
                  "logs:PutLogEvents"
                ],
                "Resource": "*"
              }]
            }
          },
          {
            "PolicyName": "AmazonS3GetObject",
            "PolicyDocument": {
              "Version": "2012-10-17",
              "Statement": [{
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": [
                  "arn:aws:s3:::pj-lambda-functions/",
                  "arn:aws:s3:::pj-lambda-functions/*"
                ]
              }]
            }
          }
        ]
      }
    }
  }
}
```

Some explanation of important keys:

- `"LambdaRole"`: this key is referred to in AWS documentation as the _logical name_ of  a resource. You can name it whatever you would like, given that the name is unique within the stack.
-  `"Properties.RoleName"`: This name must be unique among roles in your entire AWS account. Having a named role is handy when assigning it to resources and convenient if the name allows someone to quickly understand what the role is for.
- `AssumeRolePolicyDocument.Principal.Service`: This defines the resource(s) that the role can be assumed by (used by). In general it is a good idea to limit roles to the minimum access needed, this includes limiting what services can use the role in the first place.
- `Policies.PolicyName`: This can be anything, it should be descriptive so that it is easy to understand what this role does.
- `PolicyDocument.Statement.Action`: The value of this key defines what this role can do and therefore is quite powerful.
- `PolicyDocument.Statement.Resource`: This defines on which resources the Actions can be performed, and again, therefore very powerful.

While all the keys in the template are important and have their own significance, the above highlighted keys are what define the nuts and bolts of a template. I find that these are the most foundational and therefore the most important to understand first. For a complete overview, see the [documentation](https://docs.aws.amazon.com/iam/?id=docs_gateway).

Now via the command line, validate the template:

```
aws cloudformation validate-template \
  --template-body file://./cf_roles.json
```

If the template is _invalid_ an error will show up in the console. Though it is not always a straight forward message, this can be a helpful step to trouble shoot errors.

Once the template passes validation, create the role:

```sh
$ aws cloudformation create-stack \
  --stack-name pj-boomer-api-roles \
  --template-body file://./cloudformation/roles.json \
  --capabilities CAPABILITY_NAMED_IAM
```

If successful, this will result in output that looks like:
```
{
    "StackId": "arn:aws:cloudformation:us-east-1:1234567890:stack/pj-boomer-api-roles/a7example80-1dd3-21ra-8a7f-0a14example08d"
}
```

**Why separate roles from other resources?**
It may have been noticed in the Project Setup that there are two separate files in the _cloudformation/_ directory, _roles.json_ and _resources.json_. Roles are powerful as they have the ability to breach our security or rack up the bill when used incorrectly. Typically roles don't need to be edited as often as other resources and can be shared between stacks if their templates are defined with this in mind. For these reasons, it is a good idea to separate them into their own template.


#### Lambda Function

Write a simple python function that will be executed when the Lambda is invoked.

In _function.py_:
```
import json

def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {'content': 'application/json'},
        "body": json.dumps({'message': 'Ok, Boomer'})
    }

```

#### Zip It

AWS Lambda requires a zip file containing the complete function code. Note that if this function required any external dependencies (outside of what is included natively in Python), then those dependencies would have to be zipped up in this file as well. As this function is extremely simple, it is only necessary to zip the _function.py_ file.

```sh
$ zip boomer-handler.zip function.py
```

#### Test Lambda Code

To test that the function code is working, create a test lambda from the command line. This lambda is only for testing, it can be deleted later. First retrieve the `Arn` of the role you just created:

```sh
$ aws iam get-role --role-name pj-basic-lambda
```
From this console output, copy and paste the `Arn` value into the command below as the `--role` argument.

```sh
$ aws lambda create-function --function-name handler-test --zip-file fileb://function.zip --handler function.handler --runtime python3.6 --role <UpdateArn>
```
Invoke the function:
```sh
$ aws lambda invoke --function-name handler-test output.txt
$ cat output.txt | jq
```

The output should look like this:
```
{
  "isBase64Encoded": false,
  "statusCode": 200,
  "headers": {
    "content": "application/json"
  },
  "multiValueHeaders": {},
  "body": "{\"message\": \"Ok, Boomer\"}"
}
```

#### Upload Code to S3 Bucket

To create a Lambda via CloudFormation, the function code needs to exist in an S3 bucket. I have chosen to pre-pend the bucket name with my initials ,`pj`, to avoid naming collisions in the future. Make a bucket where the function code will live:

```sh
$ aws s3 mb pj-lambda-code
```

Upload the zip file:

```sh
$ aws s3 cp ./boomer-handler.zip s3://pj-lambda-code/boomer-handler.zip
```

Verify that the upload was successful:
```sh
$ aws s3 ls s3://pj-lambda-code/
```

The zip file should be listed in the console output.

## Lambda, APIGateway in CloudFormation

CloudFormation templates, when run via the AWS CLI or the AWS console, create _stacks_. A _stack_ is a collection of AWS resources that you can manage as a single unit. Some of the benefits of stacks:
- associate functioning units of infrastructure rather than manage systems resource by resource
- ensure that when updating a stack all resources are updated at the same time
- automatic versioning
- automatic rollback if a deployment is not successful


### Lambda in CloudFormation

At this point, a role with the necessary permissions has been created and a working lambda function has been written and tested. Next, this lambda function will be the first resource defined in the _cloudformation/resources.json_ file.

> [AWS CloudFormation Docs for Lambda Functions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-function.html)

Add this to the _resources.json_:

```
{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "BoomerHandler": {
      "Type": "AWS::Lambda::Function",
      "Properties": {
        "FunctionName": "BoomerHandler",
        "Handler": "function.handler",
        "Role": "arn:aws:iam::0123456789:role/pj-basic-lambda",
        "Code": {
          "S3Bucket": "pj-lambda-code",
          "S3Key": "boomer-handler.zip"
        },
        "Runtime": "python3.6"
      }
    }
  }
}
```

Some explanation:

- `"BoomerHandler": {...}`: this key is referred to in AWS documentation as the _logical name_ of a resource. You can name it whatever you would like, given that it is unique within the stack.
- `"Type": "AWS::Lambda::Function"`: this defines what type resource is being created.
- `"Handler": "function.handler"`: this refers to the file name and function name that exists within the zip file that this function will reference. The value for this key varies by runtime (programming language), [here are the docs for each](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-features.html).
- `"Role": "arn:aws:iam::0123456789:role/pj-basic-lambda"`: the role arn that will be associated to this lambda granting it the necessary permissions. In this case the arn from the role that was created earlier in the tutorial.

To test, use the AWS CLI to invoke the function:
```sh
$ aws lambda invoke --function-name handler-test output.txt
$ cat output.txt | jq
```

The output should be the same as the last time it was tested:

```
{
  "isBase64Encoded": false,
  "statusCode": 200,
  "headers": {
    "content": "application/json"
  },
  "multiValueHeaders": {},
  "body": "{\"message\": \"Ok, Boomer\"}"
}
```

### APIGateway

To establish an APIGateway, five resources need to be created:
- **Role**
- **RestAPI**
- **Method**
- **Deployment**
- **Stage**

The next section provides a brief description on what these resources are and how to configure them via CloudFormation.

#### APIGateway Role

This json is to be added to the `"Resources"` object of the existing _cloudformation/roles.json_ template:

```
"ApiGatewayRole": {
  "Type": "AWS::IAM::Role",
  "Properties": {
    "RoleName": "pj-api-for-lambda",
    "AssumeRolePolicyDocument": {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {
          "Service": ["apigateway.amazonaws.com"]
        },
        "Action": ["sts:AssumeRole"]
      }]
    },
    "Policies": [{
        "PolicyName": "AWSApiGateWay",
        "PolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "*"
          }]
        }
      },
      {
        "PolicyName": "ApiGatewayFullAccess",
        "PolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Action": [
              "apigateway:*"
            ],
            "Resource": "*"
          }]
        }
      }
    ]
  }
}
```

> SECURITY: in the above definition, the resources field in both policies are set to `"*"`. This represents a security risk and is discouraged in favor of defining the specific resources that this role has permission to act on.


#### Rest API

The  **RestAPI** resource will be the 'parent' of the other related resources.

> [AWS _APIGateway:RestAPI_ CloudFormation Docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-restapi.html)


```
"BoomerApi": {
  "Type": "AWS::ApiGateway::RestApi",
  "Properties": {
    "Name": "boomer-api",
    "Description": "API used for practice",
    "FailOnWarnings": true
  }
}
```

#### Method

The **Method** resource defines an HTTP method and how a request to that method is fulfilled.

> [AWS _APIGateway:Method_ CloudFormation Docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-method.html)


In this definition, there are a couple new pieces of syntax known as _Intrinsic Functions_ which were discussed briefly in the introduction. Generally, the reader can reason out what these functions are doing. Refer to the [AWS Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html) for more information.

As  well, notice the `DependsOn` key. This Method definition requires the RestApiId and ResourceId be defined when created. The DependsOn key ensure that the BoomerApi will be created before this definition is evaluated.

```
"RootGet": {
  "Type": "AWS::ApiGateway::Method",
  "DependsOn": ["BoomerApi"],
  "Properties": {
    "RestApiId": {
      "Ref": "BoomerApi"
    },
    "ResourceId": {
      "Fn::GetAtt": [
        "BoomerApi",
        "RootResourceId"
      ]
    },
    "HttpMethod": "GET",
    "AuthorizationType": "NONE",
    "Integration": {
      "Credentials": "ARN from APIGATEWAY role"
      },
      "IntegrationHttpMethod": "POST",
      "Type": "AWS_PROXY",
      "Uri": {
        "Fn::Join": ["",
          [
            "arn:aws:apigateway:",
            {
              "Ref": "AWS::Region"
            },
            ":lambda:path/2015-03-31/functions/",
            {
              "Fn::GetAtt": ["BoomerHandler", "Arn"]
            },
            "/invocations"
          ]
        ]
      }
    }
  }
}
```

#### Deployment

A **Deployment** represents a snapshot of a rest API and is necessary for the RestAPI to function.

> [AWS _APIGateway:Deployment_ CloudFormation Docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-deployment.html)

Again, note the `DependsOn` key: a Deployment must wait for Method(s) to be created, or else it will throw an error and the stack will fail to be created/updated.

```
"Deployment": {
  "DependsOn": ["BoomerApi", "RootGet"],
  "Type": "AWS::ApiGateway::Deployment",
  "Properties": {
    "RestApiId": {
      "Ref": "BoomerApi"
    }
  }
}
```

#### Stage

A **Stage** defines a pathway to a deployment of an API. It can be used to configure specific settings like caching, logging, as well as defining stage specific variables.

> [AWS _APIGateway:Stage_ CloudFormation Docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-stage.html)

Finally, a Stage acts like a version or snapshot of the rest api.

```
"Stage": {
  "DependsOn": ["BoomerApi", "Deployment"],
  "Type": "AWS::ApiGateway::Stage",
  "Properties": {
    "StageName": "dev",
    "RestApiId": {
      "Ref": "BoomerApi"
    },
    "DeploymentId": {
      "Ref": "Deployment"
    }
  }
}
```

## Deploy and Test

### Deploy

```
$ aws cloudformation create-stack --stack-name pj-boomer-api --template-body file://./cloudformation/resources.json
```

If successful, this will print to the console:
```
{
    "StackId": "arn:aws:cloudformation:us-east-1:0123456789:stack/pj-boomer-api/93000120-10c9-12da-bdc0-0example0da"
}
```

### Test

First, retrieve the RestAPI id:
```sh
$ aws apigateway get-rest-apis
```
This will output:
```
{
    "items": [
        {
            "id": "w7example1c",
            "name": "boomer-api",
            "description": "API used for practice",
            "createdDate": 1576036320,
            "apiKeySource": "HEADER",
            "endpointConfiguration": {
                "types": [
                    "EDGE"
                ]
            }
        }
    ]
}
```

Copy the id, paste it into this url format, and run the curl command:
```
# default format: https://<restApiId>.execute-api.<awsRegion>.amazonaws.com/<stageName>

curl -X GET https://w7example1c.execute-api.us-east-1.amazonaws.com/dev
```

If all is working, `{"message": "Ok Boomer"}` will print to the console.

At this point in the tutorial we have achieved a complete API hosted in AWS that is defined in code, version controlled, repeatable and its components are grouped into composable stacks making future releases and updates simple.

Congratulations on completing this set of tasks!

## Consolidate

In an effort to make these stacks more readable, maintainable and reusable, certain values can be abstracted into Parameters and Outputs.

### Use Parameters

Parameters allow the template to take in values dynamically when creating or updating a stack. As well, by taking advantage of default values the parameters to remove redundancy from the template and they serve to highlight custom values making the code easier to read.

> [AWS CloudFormation Parameters Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html)

Add this object to the top level of the `cloudformation/resources.json` json:
```
"Parameters": {
  "RolesStack": {
    "Type": "String",
    "Default": "pj-boomer-api-roles"
  },
  "HandlerCodeS3Bucket": {
    "Type": "String",
    "Default": "pj-lambda-functions"
  },
  "HandlerCodeS3Key": {
    "Type": "String",
    "Default": "boomer-api.zip"
  }
}
```

Update these values to reference the parameters:

|Key|Value|
|----|-----|
|`Resources.BoomerHandler.Properties.Code.S3Bucket`|`{ "Ref": "HandlerCodeS3Bucket"}`|
|`Resources.BoomerHandler.Properties.Code.S3Key`|`{ "Ref": "HandlerCodeS3Key"}`|
|`Resources.RootGet.Properties.RestApiId`|`{ "Ref": "BoomerApi"}`|
|`Resources.Deployment.Properties.RestApiId`|`{ "Ref": "BoomerApi"}`|
|`Resources.Stage.Properties.RestApiId`|`{ "Ref": "BoomerApi"}`|
|`Resources.Stage.Properties.DeploymentId`|`{ "Ref": "Deployment"}`|

Have a look at the [final _resources.json_ template](https://github.com/topleft/boomer-api/blob/master/cloudformation/resources.json) to see the parameters in context.

And in the _cloudformation/roles.json_ there are a couple values that could benefit from using parameters. Update the code to this:

```
"Parameters": {
  "LambdaFnS3Bucket": {
    "Type": "String",
    "Default": "pj-lambda-functions"
  },
  "LambdaResources": {
    "Type": "CommaDelimitedList",
    "Default": "*",
    "Description": "Lambda resources (arn:aws:lambda:us-west-2:aws-account-number:function:my-function) in the form of a comma separated string that this api will need to invoke. Defaults to * but should be updated once the lambda(s) is/are created."
  }
},
"Resources": {
  "LambdaRole": {
    "Type": "AWS::IAM::Role",
    "Properties": {
      "RoleName": "pj-basic-lambda",
      "AssumeRolePolicyDocument": {
        "Version": "2012-10-17",
        "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": ["lambda.amazonaws.com"]
          },
          "Action": ["sts:AssumeRole"]
        }]
      },
      "Path": "/",
      "Policies": [{
          "PolicyName": "AWSLambdaBasicExecutionRole",
          "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
              "Effect": "Allow",
              "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ],
              "Resource": "*"
            }]
          }
        },
        {
          "PolicyName": "AmazonS3GetObject",
          "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
              "Effect": "Allow",
              "Action": "s3:GetObject",
              "Resource": [{
                  "Fn::Sub": "arn:aws:s3:::${LambdaFnS3Bucket}/"
                },
                {
                  "Fn::Sub": "arn:aws:s3:::${LambdaFnS3Bucket}/*"
                }
              ]
            }]
          }
        }
      ]
    }
  }
}
```

The `LambdaResources` parameters is defaulting to `*`, which allows this template to be usable without overriding the default, but like stated earlier, this is a security vulnerability. For this project when the stack is updated, `--parameters LambdaFnS3Bucket=pj-lambda-functions` should be added to the command to limit what resources this role can access.

Have a look at the [final _roles.json_ template](https://github.com/topleft/boomer-api/blob/master/cloudformation/roles.json) to see the parameters in context.


### Use outputs

The power of `Outputs` is that they allow values to be shared across stacks. From the _roles stack_ there are two values that are needed in the _resources stack_. Rather than look them up and then hard code them which would be brittle and not reusable, they can be exported from the _cloudformation/roles.json_ and the imported in the _cloudformation/resources.json_.

> [AWS CloudFormation Outputs Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html)

Add this json to the _cloudformation/roles.json_ file:

```
"Outputs": {
  "LambdaRole": {
    "Description": "Basic Lambda Role Arn: cloudwatch and s3 access",
    "Value": {
      "Fn::GetAtt": ["LambdaRole", "Arn"]
    },
    "Export": {
      "Name": {
        "Fn::Sub": "${AWS::StackName}-LambdaRoleArn"
      }
    }
  },
  "ApiGatewayRole": {
    "Description": "Apigateway Role Arn: full apigateway and invoke lambda access",
    "Value": {
      "Fn::GetAtt": ["ApiGatewayRole", "Arn"]
    },
    "Export": {
      "Name": {
        "Fn::Sub": "${AWS::StackName}-ApiGatewayRoleArn"
      }
    }
  }
}
```

Within the above code, there are a  couple references to the `AWS::StackName` variable. This variable is populated by the `--stack-name` argument that was passed when the stack was created. This is another example of achieving reusability by implementing _Intrinsic Functions_.

Use the Outputs from the roles stack in the resources stack template:
```
"BoomerHandler": {
  "Role": {
    "Fn::ImportValue": {
      "Fn::Sub": "${RolesStack}-LambdaRoleArn"
    }
  }
}

...

"RootGet":  {
  "Properties": {
    "Integration": {
      "Credentials": {
        "Fn::ImportValue": {
          "Fn::Sub": "${RolesStack}-ApiGatewayRoleArn"
        }
      }
    }
  }
}
```

<br/>

---------------------------------


\* The phrase 'Ok, Boomer' has been thrown around the internet quite a bit these days. This theme is meant to be current and light hearted, please don't take it too seriously.
