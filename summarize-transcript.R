# audio-transcription-pipeline/transcribe.R
# ─────────────────────────────────────────────────────────────────────
# Full pipeline: WhisperX JSON → formatted transcript → LLM summary
#
# Usage:
#   source("transcribe.R")
#   result <- run_pipeline("output/my_meeting.json")
#   result <- run_pipeline("output/my_meeting.json", engine = "anthropic")
#   result <- run_pipeline("output/my_meeting.json", meeting_type = "interview")
# ─────────────────────────────────────────────────────────────────────

library(jsonlite)
library(httr2)

# ── 1. Meeting type prompt presets ────────────────────────────────────

#' Return a summarization prompt for a given meeting type.
#'
#' @param meeting_type One of: "general", "standup", "interview",
#'   "research", "lecture", "custom"
#' @param custom_prompt If meeting_type = "custom", provide your own
#'   prompt string here.
#' @return A character string prompt template (transcript appended at end)

meeting_prompt <- function(meeting_type = c("general", "standup",
                                            "interview", "research",
                                            "lecture", "grant_planning",
                                            "custom"),
                           custom_prompt = NULL) {
  meeting_type <- match.arg(meeting_type)

  presets <- list(

    general = paste0(
      "You are a professional meeting summarizer. ",
      "Given the following transcript with speaker labels and timestamps, provide:\n",
      "1. A 2-3 sentence overview of the meeting\n",
      "2. Key decisions made\n",
      "3. Action items with speaker attribution\n",
      "4. Any open questions or unresolved issues\n\n"
    ),

    standup = paste0(
      "You are summarizing a standup meeting. ",
      "Given the following transcript with speaker labels and timestamps, provide:\n",
      "1. What each speaker reported they completed\n",
      "2. What each speaker is working on today\n",
      "3. Any blockers or impediments raised\n\n"
    ),

    interview = paste0(
      "You are summarizing a research interview or conversation. ",
      "Given the following transcript with speaker labels and timestamps, provide:\n",
      "1. A 2-3 sentence overview of the conversation topic\n",
      "2. Key themes and insights from the interviewee\n",
      "3. Notable quotes or moments (with timestamps)\n",
      "4. Follow-up questions worth exploring\n\n"
    ),

    research = paste0(
      "You are summarizing a research discussion. ",
      "Given the following transcript with speaker labels and timestamps, provide:\n",
      "1. Research question or topic under discussion\n",
      "2. Key findings or arguments raised\n",
      "3. Methodological points discussed\n",
      "4. Next steps or gaps identified\n\n"
    ),

    lecture = paste0(
      "You are summarizing a lecture or presentation. ",
      "Given the following transcript with speaker labels and timestamps, provide:\n",
      "1. Main topic and learning objectives\n",
      "2. Key concepts covered (with timestamps)\n",
      "3. Examples or case studies mentioned\n",
      "4. Summary suitable for study notes\n\n"
    ),

    grant_planning = paste0(
  "You are summarizing a grant planning meeting at a Tribal College. ",
  "Given the following transcript with speaker labels and timestamps, provide:\n",
  "1. A 2-3 sentence overview of the grant or proposal under discussion\n",
  "2. Funding opportunities or mechanisms mentioned\n",
  "3. Key decisions made about approach, scope, or infrastructure\n",
  "4. Risks and open questions identified\n",
  "5. Action items with speaker attribution and any deadlines mentioned\n",
  "6. Next steps and timeline\n\n"),

    custom = custom_prompt
  )

  if (meeting_type == "custom" && is.null(custom_prompt)) {
    stop("Provide a custom_prompt string when meeting_type = 'custom'")
  }

  presets[[meeting_type]]
}


# ── 2. Parse WhisperX JSON output ─────────────────────────────────────

#' Read a WhisperX JSON output file into a data frame.
#'
#' @param json_path Path to the WhisperX JSON output file.
#' @return A data frame with columns: start, end, speaker, text

read_whisperx <- function(json_path) {
  raw <- fromJSON(path.expand(json_path), flatten = TRUE)
  data.frame(
    start   = raw$segments$start,
    end     = raw$segments$end,
    speaker = raw$segments$speaker,
    text    = trimws(raw$segments$text),
    stringsAsFactors = FALSE
  )
}


# ── 2b. Read a cleaned plain-text transcript ──────────────────────────

#' Read a human-cleaned plain-text transcript.
#'
#' @param txt_path Path to the cleaned .txt transcript file.
#' @return A character string ready for LLM input.

read_txt_transcript <- function(txt_path) {
  paste(readLines(path.expand(txt_path), warn = FALSE), collapse = "\n")
}


# ── 3. Format segments for LLM input ──────────────────────────────────

#' Format a segments data frame into a readable transcript string.
#'
#' @param segments Data frame from read_whisperx()
#' @return A character string formatted for LLM input

format_transcript <- function(segments) {
  paste0(
    "[", segments$speaker, " @ ",
    sprintf("%.1f", segments$start), "s] ",
    segments$text,
    collapse = "\n"
  )
}


# ── 4. LLM backends ───────────────────────────────────────────────────

#' Summarize a transcript using the Anthropic API.
#'
#' @param transcript Formatted transcript string
#' @param prompt     System prompt from meeting_prompt()
#' @param model      Anthropic model ID (default: claude-sonnet-4-6)
#' @param api_key    Anthropic API key (default: ANTHROPIC_API_KEY env var)
#' @return Summary as a character string

summarize_anthropic <- function(transcript,
                                prompt,
                                model   = "claude-sonnet-4-6",
                                api_key = Sys.getenv("ANTHROPIC_API_KEY")) {
  if (nchar(api_key) == 0) {
    stop("ANTHROPIC_API_KEY not set. Add it to ~/.Renviron and restart R.")
  }

  full_prompt <- paste0(prompt, "Transcript:\n", transcript)

  resp <- request("https://api.anthropic.com/v1/messages") |>
    req_headers(
      "x-api-key"         = api_key,
      "anthropic-version" = "2023-06-01",
      "content-type"      = "application/json"
    ) |>
    req_body_json(list(
      model      = model,
      max_tokens = 1024L,
      messages   = list(list(role = "user", content = full_prompt))
    )) |>
    req_perform()

  resp |> resp_body_json() |> _$content[[1]]$text
}


#' Summarize a transcript using a local Ollama model.
#'
#' @param transcript Formatted transcript string
#' @param prompt     System prompt from meeting_prompt()
#' @param model      Ollama model name (default: llama3.1:8b-instruct-q6_k)
#' @param host       Ollama server URL (default: http://127.0.0.1:11434)
#' @return Summary as a character string

summarize_ollama <- function(transcript,
                             prompt,
                             model = "llama3.1:8b-instruct-q6_k",
                             host  = "http://127.0.0.1:11434") {
  full_prompt <- paste0(prompt, "Transcript:\n", transcript)

  resp <- request(paste0(host, "/api/generate")) |>
    req_body_json(list(
      model  = model,
      prompt = full_prompt,
      stream = FALSE
    )) |>
    req_perform()

  resp |> resp_body_json() |> _$response
}


# ── 5. Save outputs ───────────────────────────────────────────────────

#' Save transcript and summary to disk.
#'
#' @param transcript  Formatted transcript string
#' @param summary     Summary string from LLM
#' @param input_path  Input file path (used to derive output filenames)
#' @param output_dir  Directory to save outputs (default: output/)

save_outputs <- function(transcript, summary, input_path,
                         output_dir = "output/processed") {
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

  base <- tools::file_path_sans_ext(basename(input_path))
  ts   <- format(Sys.time(), "%Y%m%d_%H%M%S")

  cat("── Saved ───────────────────────────────────\n")

  # Skip transcript copy when input is already a cleaned .txt
  transcript_path <- NULL
  if (tools::file_ext(input_path) != "txt") {
    transcript_path <- file.path(output_dir, paste0(base, "_transcript_", ts, ".txt"))
    writeLines(transcript, transcript_path)
    cat("Transcript:", transcript_path, "\n")
  }

  # Always save summary
  summary_path <- file.path(output_dir, paste0(base, "_summary_", ts, ".txt"))
  writeLines(summary, summary_path)
  cat("Summary:   ", summary_path, "\n\n")

  invisible(list(transcript_path = transcript_path,
                 summary_path    = summary_path))
}


# ── 6. Full pipeline ──────────────────────────────────────────────────

#' Run the full transcription and summarization pipeline.
#'
#' @param input_path  Path to input file: cleaned .txt (recommended) or
#'                    raw WhisperX .json (quick path, no human review)
#' @param engine       LLM backend: "ollama" (local/free) or "anthropic" (API)
#' @param meeting_type Prompt preset: "general", "standup", "interview",
#'                     "research", "lecture", or "custom"
#' @param custom_prompt If meeting_type = "custom", your prompt string
#' @param save         Whether to save transcript and summary to disk
#' @param output_dir   Directory for saved outputs
#' @param ...          Additional args passed to summarize_anthropic() or
#'                     summarize_ollama() (e.g., model = "llama3.1:latest")
#'
#' @return Invisibly returns a list with: segments, transcript, summary,
#'         and (if save = TRUE) output file paths
#'
#' @examples
#' # Cleaned .txt — recommended path
#' result <- run_pipeline(
#'   "output/processed/meeting_clean.txt",
#'   engine = "anthropic",
#'   meeting_type = "general"
#' )
#'
#' # Raw JSON — quick path, no human review
#' result <- run_pipeline(
#'   "output/raw/meeting.json",
#'   engine = "anthropic",
#'   meeting_type = "general"
#' )
#'
#' # Custom prompt, local Ollama
#' result <- run_pipeline("output/processed/meeting_clean.txt",
#'                        meeting_type = "custom",
#'                        custom_prompt = "Summarize this in haiku form:\n\n")

run_pipeline <- function(input_path,
                         engine       = c("ollama", "anthropic"),
                         meeting_type = c("general", "standup", "interview",
                                          "research", "lecture",
                                          "grant_planning", "custom"),
                         custom_prompt = NULL,
                         save         = TRUE,
                         output_dir   = "output/processed",
                         ...) {
  engine       <- match.arg(engine)
  meeting_type <- match.arg(meeting_type)

  # Parse — .txt (cleaned) or .json (raw WhisperX)
  ext <- tools::file_ext(input_path)
  if (ext == "txt") {
    cat("── Reading cleaned transcript (.txt) ───────\n")
    segments   <- NULL
    transcript <- read_txt_transcript(input_path)
  } else {
    cat("── Parsing transcript (.json) ──────────────\n")
    segments   <- read_whisperx(input_path)
    transcript <- format_transcript(segments)
  }

  cat("── Transcript ──────────────────────────────\n")
  cat(transcript, "\n\n")

  # Build prompt
  prompt <- meeting_prompt(meeting_type, custom_prompt)

  # Summarize
  cat("── Summarizing via", engine, "(", meeting_type, ") ──\n")
  summary <- switch(engine,
    ollama    = summarize_ollama(transcript, prompt, ...),
    anthropic = summarize_anthropic(transcript, prompt, ...)
  )
  cat(summary, "\n\n")

  # Save
  paths <- NULL
  if (save) {
    paths <- save_outputs(transcript, summary, input_path, output_dir)
  }

  invisible(list(
    segments   = segments,
    transcript = transcript,
    summary    = summary,
    paths      = paths
  ))
}


# ── 7. Merge two summaries ─────────────────────────────────────────────

#' Merge two independently generated summaries using an LLM.
#'
#' @param summary1  First summary string
#' @param summary2  Second summary string
#' @param engine    LLM backend: "ollama" or "anthropic"
#' @param model     Override model (default: same as summarize_* functions)
#' @param api_key   Anthropic API key (default: ANTHROPIC_API_KEY env var)
#' @param host      Ollama server URL
#' @return Merged summary as a character string

merge_summaries <- function(summary1, summary2, engine,
                             model   = NULL,
                             api_key = Sys.getenv("ANTHROPIC_API_KEY"),
                             host    = "http://127.0.0.1:11434") {

  full_prompt <- paste0(
    "You are merging two independently generated summaries of the same meeting. ",
    "Produce one comprehensive summary that includes all unique information from both. ",
    "Do not duplicate content. Where the summaries differ on the same point, prefer ",
    "the more specific or detailed version. Preserve all section headings.\n\n",
    "Summary A:\n", summary1, "\n\n",
    "Summary B:\n", summary2
  )

  if (engine == "anthropic") {
    if (is.null(model)) model <- "claude-sonnet-4-6"
    resp <- request("https://api.anthropic.com/v1/messages") |>
      req_headers(
        "x-api-key"         = api_key,
        "anthropic-version" = "2023-06-01",
        "content-type"      = "application/json"
      ) |>
      req_body_json(list(
        model      = model,
        max_tokens = 2048L,
        messages   = list(list(role = "user", content = full_prompt))
      )) |>
      req_perform()
    resp |> resp_body_json() |> _$content[[1]]$text

  } else {
    if (is.null(model)) model <- "llama3.1:8b-instruct-q6_k"
    resp <- request(paste0(host, "/api/generate")) |>
      req_body_json(list(
        model  = model,
        prompt = full_prompt,
        stream = FALSE
      )) |>
      req_perform()
    resp |> resp_body_json() |> _$response
  }
}


# ── 8. Merged pipeline ────────────────────────────────────────────────

#' Run the pipeline twice and merge the results for a more complete summary.
#'
#' LLM outputs are non-deterministic: two runs of the same prompt will
#' capture different details. This function runs the summarizer twice,
#' then uses the LLM to merge both outputs into one comprehensive summary.
#'
#' @param input_path   Path to cleaned .txt (recommended) or raw .json
#' @param engine       LLM backend: "ollama" or "anthropic"
#' @param meeting_type Prompt preset
#' @param custom_prompt Your own prompt string (if meeting_type = "custom")
#' @param save         Whether to save merged summary to disk
#' @param output_dir   Directory for saved outputs
#' @param ...          Additional args passed to summarize_* functions
#'
#' @return Invisibly: list with transcript, summary1, summary2,
#'         summary_merged, and paths

run_pipeline_merged <- function(input_path,
                                 engine        = c("ollama", "anthropic"),
                                 meeting_type  = c("general", "standup", "interview",
                                                   "research", "lecture",
                                                   "grant_planning", "custom"),
                                 custom_prompt = NULL,
                                 save          = TRUE,
                                 output_dir    = "output/processed",
                                 ...) {
  engine       <- match.arg(engine)
  meeting_type <- match.arg(meeting_type)

  # Parse
  ext <- tools::file_ext(input_path)
  if (ext == "txt") {
    cat("── Reading cleaned transcript (.txt) ───────\n")
    segments   <- NULL
    transcript <- read_txt_transcript(input_path)
  } else {
    cat("── Parsing transcript (.json) ──────────────\n")
    segments   <- read_whisperx(input_path)
    transcript <- format_transcript(segments)
  }

  prompt <- meeting_prompt(meeting_type, custom_prompt)

  cat("── Run 1 ───────────────────────────────────\n")
  summary1 <- switch(engine,
    ollama    = summarize_ollama(transcript, prompt, ...),
    anthropic = summarize_anthropic(transcript, prompt, ...)
  )

  cat("── Run 2 ───────────────────────────────────\n")
  summary2 <- switch(engine,
    ollama    = summarize_ollama(transcript, prompt, ...),
    anthropic = summarize_anthropic(transcript, prompt, ...)
  )

  cat("── Merging ─────────────────────────────────\n")
  summary_merged <- merge_summaries(summary1, summary2, engine)
  cat(summary_merged, "\n\n")

  paths <- NULL
  if (save) {
    paths <- save_outputs(transcript, summary_merged, input_path, output_dir)
  }

  invisible(list(
    segments       = segments,
    transcript     = transcript,
    summary1       = summary1,
    summary2       = summary2,
    summary_merged = summary_merged,
    paths          = paths
  ))
}
