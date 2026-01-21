from pathlib import Path
from uuid import UUID

import hypothesis.strategies as st
from pydantic import BaseModel, computed_field


class RunFolder:
    FASTQC_LIST = "Analysis/1/Data/BCLConvert/fastq/Reports/fastq_list.csv"
    DEMULTIPLEX_STATS = "Analysis/1/Data/BCLConvert/fastq/Reports/Demultiplex_Stats.csv"
    QUALITY_METRICS = "Analysis/1/Data/BCLConvert/fastq/Reports/Quality_Metrics.csv"

    def __init__(self, root: Path):
        self.root = root

        # Initialize paths
        ## fastqc_list
        self.fastqc_list_path = Path(self.root, self.FASTQC_LIST)
        self.fastqc_list_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fastqc_list_path, "w") as f:
            f.write("RGID,RGSM,RGLB,Lane,Read1File,Read2File\n")

        # demultiplex_stats
        self.demultiplex_stats_path = Path(self.root, self.DEMULTIPLEX_STATS)
        self.demultiplex_stats_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.demultiplex_stats_path, "w") as f:
            f.write(
                ",".join(
                    [
                        "Lane",
                        "SampleID",
                        "Sample_Project",
                        "Index",
                        "# Reads",
                        "# Perfect Index Reads",
                        "# One Mismatch Index Reads",
                        "# Two Mismatch Index Reads",
                        "% Reads",
                        "% Perfect Index Reads",
                        "% One Mismatch Index Reads",
                        "% Two Mismatch Index Reads",
                    ]
                )
                + "\n"
            )

        # quality_metrics
        self.quality_metrics_path = Path(self.root, self.QUALITY_METRICS)
        self.quality_metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.quality_metrics_path, "w") as f:
            f.write(
                ",".join(
                    [
                        "Lane",
                        "SampleID",
                        "Sample_Project",
                        "index",
                        "index2",
                        "ReadNumber",
                        "Yield",
                        "YieldQ30",
                        "QualityScoreSum",
                        "Mean Quality Score (PF)",
                        "% Q30",
                    ]
                )
                + "\n"
            )

        # Write marker file
        marker_file = Path(
            self.root, "Analysis/1/Data/BCLConvert/fastq/Logs/FastqComplete.txt"
        )
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        with open(marker_file, "w") as f:
            f.write("Fastq generation complete.\n")

    def _create_fastq_files(
        self, samples: list[PairedReadSampleTestData] | list[SingleReadSampleTestData]
    ):
        for sample in samples:
            if isinstance(sample, PairedReadSampleTestData):
                paths = [sample.fastq_read1_path, sample.fastq_read2_path]
            else:
                paths = [sample.fastq_read1_path]
            for path in paths:
                assert not path.is_absolute(), (
                    "Fastq paths must be relative in this test setup"
                )
                absolute_path = (Path(self.fastqc_list_path).parent / path).resolve()
                assert absolute_path.is_relative_to(self.root), (
                    "Fastq paths must be within the runfolder"
                )
                absolute_path.parent.mkdir(parents=True, exist_ok=True)
                with open(absolute_path, "w") as f:
                    f.write("")  # create empty file

    def _write_fastqc_list(
        self, samples: list[PairedReadSampleTestData] | list[SingleReadSampleTestData]
    ):
        with open(self.fastqc_list_path, "a") as f:
            for sample in samples:
                f.write(
                    ",".join(
                        [
                            "AAAAAAAA.CCCCCCC.1",  # RGID
                            sample.name,  # RGSM
                            "LIBRARY1",  # RGLB
                            "1",  # Lane
                            sample.fastq_read1_path.as_posix(),  # Read1File
                            sample.fastq_read2_path.as_posix()
                            if isinstance(sample, PairedReadSampleTestData)
                            else "",  # Read2File
                        ]
                    )
                    + "\n"
                )

    def _write_demux_stats(
        self, samples: list[PairedReadSampleTestData] | list[SingleReadSampleTestData]
    ):
        with open(self.demultiplex_stats_path, "a") as f:
            for sample in samples:
                f.write(
                    ",".join(
                        [
                            "1",  # Lane
                            sample.name,  # SampleID
                            "Project_1",  # Sample_Project
                            "ATCG-GCTA",  # Index
                            str(sample.num_reads),  # # Reads
                            str(
                                sample.num_perfect_index_reads
                            ),  # # Perfect Index Reads
                            str(
                                sample.num_one_mismatch_index_reads
                            ),  # # One Mismatch Index Reads
                            str(
                                sample.num_two_mismatch_index_reads
                            ),  # # Two Mismatch Index Reads
                            f"{sample.percent_reads:.4f}",  # % Reads
                            f"{sample.percent_perfect_index_reads:.4f}",  # % Perfect Index Reads
                            f"{sample.percent_one_mismatch_index_reads:.4f}",  # % One Mismatch Index Reads
                            f"{sample.percent_two_mismatch_index_reads:.4f}",  # % Two Mismatch Index Reads
                        ]
                    )
                    + "\n"
                )

    def _write_quality_metrics(
        self, samples: list[PairedReadSampleTestData] | list[SingleReadSampleTestData]
    ):
        with open(self.quality_metrics_path, "a") as f:
            for sample in samples:
                # Read 1
                f.write(
                    ",".join(
                        [
                            "1",  # Lane
                            sample.name,  # SampleID
                            "Project_1",  # Sample_Project
                            "ATCG",  # index
                            "GCTA",  # index2
                            "1",  # ReadNumber
                            str(sample.r1_yield),  # Yield
                            str(sample.r1_yield_q30),  # YieldQ30
                            str(sample.r1_quality_score_sum),  # QualityScoreSum
                            f"{sample.r1_mean_quality_score:.2f}",  # Mean Quality Score (PF)
                            f"{sample.r1_percentage_q30:.4f}",  # % Q30
                        ]
                    )
                    + "\n"
                )
                if isinstance(sample, PairedReadSampleTestData):
                    # Read 2
                    f.write(
                        ",".join(
                            [
                                "1",  # Lane
                                sample.name,  # SampleID
                                "Project_1",  # Sample_Project
                                "ATCG",  # index
                                "GCTA",  # index2
                                "2",  # ReadNumber
                                str(sample.r2_yield),  # Yield
                                str(sample.r2_yield_q30),  # YieldQ30
                                str(sample.r2_quality_score_sum),  # QualityScoreSum
                                f"{sample.r2_mean_quality_score:.2f}",  # Mean Quality Score (PF)
                                f"{sample.r2_percentage_q30:.4f}",  # % Q30
                            ]
                        )
                        + "\n"
                    )

    def write_samples(
        self, samples: list[PairedReadSampleTestData] | list[SingleReadSampleTestData]
    ):
        self._create_fastq_files(samples)
        self._write_fastqc_list(samples)
        self._write_demux_stats(samples)
        self._write_quality_metrics(samples)


class SingleReadSampleTestData(BaseModel):
    name: str = "Sample"
    uuid: UUID
    r1_yield: int
    r1_mean_quality_score: float
    r1_percentage_q30: float
    percent_reads: float
    percent_perfect_index_reads: float
    percent_one_mismatch_index_reads: float
    percent_two_mismatch_index_reads: float

    @computed_field
    @property
    def num_reads(self) -> int:
        return self.r1_yield * 151  # assuming 151 bp reads

    @computed_field
    @property
    def num_perfect_index_reads(self) -> int:
        return int(self.num_reads * 0.9)  # assuming 90% perfect index reads

    @computed_field
    @property
    def num_one_mismatch_index_reads(self) -> int:
        return int(self.num_reads * 0.05)  # assuming 5% one mismatch index reads

    @computed_field
    @property
    def num_two_mismatch_index_reads(self) -> int:
        return int(self.num_reads * 0.03)  # assuming 3% two mismatch index reads

    @computed_field
    @property
    def fastq_read1_path(self) -> Path:
        return Path(f"../{self.name}_R1_001.fastq.gz")

    @computed_field
    @property
    def r1_quality_score_sum(self) -> int:
        return int(self.r1_mean_quality_score * self.r1_yield)

    @computed_field
    @property
    def r1_yield_q30(self) -> int:
        return int(self.r1_yield * self.r1_percentage_q30)


class PairedReadSampleTestData(SingleReadSampleTestData):
    r2_yield: int
    r2_mean_quality_score: float
    r2_percentage_q30: float

    @computed_field
    @property
    def fastq_read2_path(self) -> Path:
        return Path(f"../{self.name}_R2_001.fastq.gz")

    @computed_field
    @property
    def r2_yield_q30(self) -> int:
        return int(self.r2_yield * self.r2_percentage_q30)

    @computed_field
    @property
    def r2_quality_score_sum(self) -> int:
        return int(self.r2_mean_quality_score * self.r2_yield)


test_paired_sample_strategy = st.builds(
    PairedReadSampleTestData,
    uuid=st.uuids(version=4),
    r1_yield=st.integers(int(5e10), int(1e11)),
    r2_yield=st.integers(int(5e10), int(1e11)),
    r1_mean_quality_score=st.floats(32, 42),
    r2_mean_quality_score=st.floats(32, 42),
    r1_percentage_q30=st.floats(0.85, 0.999),
    r2_percentage_q30=st.floats(0.85, 0.999),
    percent_reads=st.floats(0.0001, 0.05),
    percent_perfect_index_reads=st.floats(0.8, 0.99),
    percent_one_mismatch_index_reads=st.floats(0.01, 0.1),
    percent_two_mismatch_index_reads=st.floats(0.001, 0.05),
)

test_single_read_sample_strategy = st.builds(
    SingleReadSampleTestData,
    uuid=st.uuids(version=4),
    r1_yield=st.integers(int(5e10), int(1e11)),
    r1_mean_quality_score=st.floats(32, 42),
    r1_percentage_q30=st.floats(0.85, 0.999),
    percent_reads=st.floats(0.0001, 0.05),
    percent_perfect_index_reads=st.floats(0.8, 0.99),
    percent_one_mismatch_index_reads=st.floats(0.01, 0.1),
    percent_two_mismatch_index_reads=st.floats(0.001, 0.05),
)


@st.composite
def build_single_read_sample(draw):
    sample = draw(test_single_read_sample_strategy)
    sample.name = f"Sample_1_{str(sample.uuid)}"
    return sample


@st.composite
def build_paired_read_sample(draw):
    sample = draw(test_paired_sample_strategy)
    sample.name = f"Sample_1_{str(sample.uuid)}"
    return sample


@st.composite
def build_samples(draw):
    samples = draw(st.lists(test_paired_sample_strategy, min_size=1, max_size=64))
    for i, sample in enumerate(samples):
        sample.name = f"Sample_{i + 1}_{str(sample.uuid)}"
    return samples
