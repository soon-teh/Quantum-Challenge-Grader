#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# (C) Copyright IBM 2022
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import json

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from qiskit import execute
from qiskit_ibm_provider.job import IBMCircuitJob as IBMQJob

from .api import (
    get_access_token,
    get_grading_endpoint,
    get_problem_set_endpoint,
    get_submission_endpoint,
    send_request,
    do_grade_only
)
from .common import (
    ValidationResult,
    calc_depth,
    get_provider,
    serialize_answer
)


def grade(
    answer: Any,
    question: Union[str, int],
    challenge: Optional[str] = None,
    return_response: Optional[str] = False,
    **kwargs: Any
) -> Tuple[bool, Optional[Union[str, int, float]], Optional[Union[str, int, float]]]:
    serialized_answer = serialize_answer(answer, **kwargs)
    do_submit = not do_grade_only()

    if challenge is None and '/' in str(question):
        challenge_id = question.split('/')[0]
        question_id = question.split('/')[1]
    else:
        question_id = question
        challenge_id = challenge

    if do_submit:
        endpoint = get_submission_endpoint(question_id, challenge_id)
        payload = {
            'question_name': question_id,
            'challenge_id': challenge_id,
            'content': serialized_answer
        }
    else:
        endpoint = get_grading_endpoint(question_id, challenge_id)
        payload = {'answer': serialized_answer}

    if serialized_answer is not None and endpoint:
        print(f'{"Submitting" if do_submit else "Grading"} your answer. Please wait...')

        result = grade_answer(
            payload,
            endpoint,
            do_submit=do_submit,
            max_content_length=kwargs['max_content_length'] if 'max_content_length' in kwargs else None,
            return_response=return_response
        )

        if return_response:
            return result
    else:
        handle_grade_response('failed')


def grade_answer(
    payload: Dict[str, str],
    endpoint: str,
    do_submit: Optional[bool] = False,
    max_content_length: Optional[int] = None,
    return_response: Optional[bool] = False
) -> Tuple[bool, Optional[Union[str, int, float]], Optional[Union[str, int, float]]]:
    try:
        access_token = get_access_token()
        if access_token:
            header = {'Authorization': f'Bearer {access_token}'}
        else:
            header = None

        answer_response = send_request(
            endpoint,
            body=payload,
            header=header,
            max_content_length=max_content_length
        )
    
        if do_submit:
            data = answer_response.get('data', {})
            status = data.get('grading_validation', None)
            cause = data.get('grading_error', None)
            score = data.get('grading_score', None)
        else:
            status = answer_response.get('status', None)
            cause = answer_response.get('cause', None)
            score = answer_response.get('score', None)

        if return_response:
            s = status == 'valid' or status is True
            return s, score, cause

        if do_submit:
            handle_submit_response(status, score=score, cause=cause)
        else:
            handle_grade_response(status, score=score, cause=cause)

    except Exception as err:
        print(f'Failed: {err}')
        return False, None, str(err)


def display_special_message(message: str, preamble='') -> None:
    if message.startswith('data:image/'):
        from IPython.display import display
        from ipywidgets import HTML
        print(preamble)
        display(HTML(f'<img src="{message}" />'))
    else:
        print(message)


def handle_grade_response(
    status: Optional[str], score: Optional[int] = None, cause: Optional[str] = None
) -> None:
    if status == 'valid' or status is True:
        if cause is not None:
            display_special_message(cause, preamble='\nCongratulations 🎉! Your answer is correct.')
        else:
            print('\nCongratulations 🎉! Your answer is correct.')
        if score is not None:
            print(f'Your score is {score}.')
    elif status == 'invalid':
        print(f'\nOops 😕! {"Your answer is incorrect" if cause is None else cause}')
        print('Please review your answer and try again.')
    elif status == 'notFinished':
        print(f'Job has not finished: {cause}')
        print(f'Please wait for the job to complete then try again.')
    else:
        print(f'Failed: {cause}')
        print('Unable to grade your answer.')


def handle_submit_response(
    status: Union[str, bool], cause: Optional[str] = None, score: Optional[int] = None
) -> None:
    if status == 'valid' or status is True:
        if cause is not None:
            display_special_message(cause, preamble='\nCongratulations 🎉! Your answer is correct.')
        else:
            print('Congratulations 🎉! Your answer is correct and has been submitted.')
        if score is not None:
            print(f'Your score is {score}.')
    elif status == 'invalid' or status is False:
        print(f'Oops 😕! {"Your answer is incorrect" if cause is None else cause}')
        # print('Make sure your answer is correct and successfully graded before submitting.')
        print('Please review your answer and try again.')
    elif status == 'notFinished':
        print(f'Job has not finished: {cause}')
        print(f'Please wait for the job to complete, grade it, and then try to submit again.')
    else:
        print(f'Failed: {cause}')
        print('Unable to submit your answer at this time.')


def get_problem_set(
    question_id: Union[str, int],
    challenge_id: str,
) -> Union[List[Dict[str, Any]], Tuple[int, Any]]:
    problem_set_response = None

    endpoint = get_problem_set_endpoint(question_id, challenge_id)

    if not endpoint:
        return None, None

    try:
        access_token = get_access_token()
        if access_token:
            header = {'Authorization': f'Bearer {access_token}'}
        else:
            header = None

        problem_set_response = send_request(endpoint, method='GET', header=header)
    except Exception as err:
        print('Unable to obtain the problem set')

    if problem_set_response:
        status = problem_set_response.get('status')
        if status == 'valid':
            try:
                index = problem_set_response.get('index')
                value = json.loads(problem_set_response.get('value'))
                return index, value
            except Exception as err:
                print(f'Problem set could not be processed: {err}')
        else:
            cause = problem_set_response.get('cause')
            print(f'Problem set failed: {cause}')

    return None, None


def run_using_problem_set(
    solver_func: Callable,
    question_id: Union[str, int],
    challenge_id: str,
    num_experiments: Optional[int] = 3,
    params_order: Optional[List[str]] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    if not callable(solver_func):
        print(f'Expected a function, but was given {type(solver_func)}')
        return None

    count = 0
    indices = []
    result_dicts = []
    while count < num_experiments:
        index, inputs = get_problem_set(question_id, challenge_id)
        if index not in indices:
            if inputs and index is not None and index >= 0:
                count += 1
                print(f'Running "{solver_func.__name__}" ({count}/{num_experiments})... ')
                if not params_order:
                    function_results = solver_func(*inputs)
                else:
                    ins = [inputs[x] for x in params_order]
                    function_results = solver_func(*ins)

                indices.append(index)
                result_dict = {
                    'index': index,
                    'problem-set': inputs,
                    'result': function_results
                }
                result_dicts.append(result_dict)
            else:
                print('Failed to obtain a valid problem set')
                return None

    return result_dicts

def prepare_solver(
    solver_func: Callable,
    question_id: Union[str, int],
    challenge_id: str,
    max_qubits: Optional[int] = 28,
    min_cost: Optional[int] = None,
    check_gates: Optional[bool] = False,
    num_experiments: Optional[int] = 4,
    params_order: Optional[List[str]] = None,
    test_problem_set: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Optional[IBMQJob]:
    job = None
    circuits = []
    indices = []

    if not callable(solver_func):
        print(f'Expected a function, but was given {type(solver_func)}')
        print(f'Please provide a function that returns a QuantumCircuit.')
        return None

    endpoint = get_grading_endpoint(question_id, challenge_id)
    if not endpoint:
        return None

    count = 0
    _, problem_sets = get_problem_set(question_id, challenge_id)
    for problem_set in problem_sets:
        index = problem_set['index']
        inputs = problem_set['value']

        if inputs and index is not None and index >= 0:
            count += 1
            print(f'Running "{solver_func.__name__}" ({count}/{len(problem_sets)})... ')
            if not params_order:
                qc = solver_func(*inputs)
            else:
                ins = [inputs[x] for x in params_order]
                qc = solver_func(*ins)

            if qc.num_qubits > max_qubits:
                print(
                    f'Your circuit has {qc.num_qubits} qubits, '
                    'which exceeds the maximum allowed.\n'
                    f'Please reduce the number of qubits in your circuit to below {max_qubits}.'
                )
                return None

            indices.append(index)
            if count < 5:
                d, n = calc_depth(qc)

            qc.metadata = {
                'qc_index': index,
                'qc_depth': json.dumps([d, n]) if count < 5 else ''
            }
            circuits.append(qc)
        else:
            print('Failed to obtain a valid problem set')
            return None

        # _, cost = _circuit_criteria(
        #     qc[n],
        #     max_qubits=max_qubits,
        #     min_cost=min_cost,
        #     check_gates=check_gates
        # )
        # costs.append(cost)

    if 'backend' not in kwargs:
        kwargs['backend'] = get_provider().get_backend('ibmq_qasm_simulator')

    # execute experiments
    print('Starting experiments. Please wait...')
    job = execute(
            circuits,
            **kwargs
        )

    print(f'You may monitor the job (id: {job.job_id()}) status '
          'and proceed to grading when it successfully completes.')

    return job
