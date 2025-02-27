import jsonpickle

from pathlib import Path
from typeguard import typechecked
from typing import Dict, Optional

from qiskit.providers import JobStatus
from qiskit_ibm_runtime import RuntimeJob
from qiskit_nature.converters.second_quantization import QubitConverter
from qiskit_nature.problems.second_quantization.electronic import ElectronicStructureProblem
from qiskit_nature.results.electronic_structure_result import ElectronicStructureResult
from qiskit_nature.runtime import VQEProgram

from qc_grader.grader.grade import grade

from .helpers import prepare_vqe_runtime_program


challenge_id = Path(__file__).parent.name


@typechecked
def grade_ex2a(answer: Dict[str, int]) -> None:
    grade(answer, '2a', challenge_id)


@typechecked
def grade_ex2b(answer: Dict[str, int]) -> None:
    grade(answer, '2b', challenge_id)


@typechecked
def grade_ex2c(result: ElectronicStructureResult) -> None:
    answer = jsonpickle.encode(result)
    grade(answer, '2c', challenge_id)


@typechecked
def grade_ex2d(result: ElectronicStructureResult) -> None:
    answer = jsonpickle.encode(result)
    grade(answer, '2d', challenge_id)


@typechecked
def grade_ex2e(result: ElectronicStructureResult) -> None:
    answer = jsonpickle.encode(result)
    grade(answer, '2e', challenge_id)


@typechecked
def prepare_ex2f(
        runtime_vqe: VQEProgram,
        qubit_converter: QubitConverter,
        problem: ElectronicStructureProblem,
        real_device: bool = False
) -> Optional[RuntimeJob]:
    return prepare_vqe_runtime_program(runtime_vqe, qubit_converter, problem, real_device)


@typechecked
def grade_ex2f(job: RuntimeJob) -> None:
    job_status = job.status()
    if job_status in [JobStatus.CANCELLED, JobStatus.ERROR]:
        print(f'Job did not successfully complete: {job_status.value}.')
    elif job_status is not JobStatus.DONE:
        print(f'Job has not yet completed: {job_status.value}.')
        print(f'Please wait for the job (id: {job.job_id()}) to complete then try again.')
    else:
        answer = jsonpickle.encode(job.result())
        grade(answer, '2f', challenge_id)
