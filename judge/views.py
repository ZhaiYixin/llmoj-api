import os

from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .JudgeServer.client.Python.client import JudgeServerClient
from .JudgeServer.client.Python.languages import c_lang_config, cpp_lang_config, java_lang_config, c_lang_spj_config, c_lang_spj_compile, py2_lang_config, py3_lang_config, go_lang_config, php_lang_config, js_lang_config

# Load environment variables from .env file
load_dotenv(override=True)
CLIENT = JudgeServerClient(token=os.getenv("JUDGE_SERVER_TOKEN"), server_base_url=os.getenv("JUDGE_SERVER_BASE_URL"))

# Create your views here.
@api_view(['POST'])
@permission_classes([])
def test(request):
    data = request.data
    c_src = data.get("c_src")
    if not c_src:
        c_src = r"""
        #include <stdio.h>
        int main(){
            int a, b;
            scanf("%d%d", &a, &b);
            printf("%d\n", a+b);
            return 0;
        }
        """
    test_case = data.get("test_case")
    if not test_case:
        test_case = [{"input": "1 2\n", "output": "3"}, {"input": "1 4\n", "output": "3"}]
    result = CLIENT.judge(src=c_src, language_config=c_lang_config, max_cpu_time=1000, max_memory=1024 * 1024 * 128, test_case=test_case, output=True)
    return Response(result, status=status.HTTP_200_OK)