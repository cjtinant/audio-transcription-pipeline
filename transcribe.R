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
                                            "lecture", "custom"),
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
#' @param json_path   Original JSON path (used to derive output filenames)
#' @param output_dir  Directory to save outputs (default: output/)

save_outputs <- function(transcript, summary, json_path,
                         output_dir = "output") {
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

  base     <- tools::file_path_sans_ext(basename(json_path))
  ts       <- format(Sys.time(), "%Y%m%d_%H%M%S")

  # Save transcript
  transcript_path <- file.path(output_dir, paste0(base, "_transcript_", ts, ".txt"))
  writeLines(transcript, transcript_path)

  # Save summary
  summary_path <- file.path(output_dir, paste0(base, "_summary_", ts, ".txt"))
  writeLines(summary, summary_path)

  cat("── Saved ───────────────────────────────────\n")
  cat("Transcript:", transcript_path, "\n")
  cat("Summary:   ", summary_path, "\n\n")

  invisible(list(transcript_path = transcript_path,
                 summary_path    = summary_path))
}


# ── 6. Full pipeline ──────────────────────────────────────────────────

#' Run the full transcription and summarization pipeline.
#'
#' @param json_path    Path to WhisperX JSON output file
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
#' # Local Ollama, general meeting
#' result <- run_pipeline("output/meeting.json")
#'
#' # Anthropic API, interview preset
#' result <- run_pipeline("output/interview.json",
#'                        engine = "anthropic",
#'                        meeting_type = "interview")
#'
#' # Custom prompt, local Ollama
#' result <- run_pipeline("output/meeting.json",
#'                        meeting_type = "custom",
#'                        custom_prompt = "Summarize this in haiku form:\n\n")

run_pipeline <- function(json_path,
                         engine       = c("ollama", "anthropic"),
                         meeting_type = c("general", "standup", "interview",
                                          "research", "lecture", "custom"),
                         custom_prompt = NULL,
                         save         = TRUE,
                         output_dir   = "output",
                         ...) {
  engine       <- match.arg(engine)
  meeting_type <- match.arg(meeting_type)

  # Parse
  cat("── Parsing transcript ──────────────────────\n")
  segments   <- read_whisperx(json_path)
  transcript <- format_transcript(segments)

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
    paths <- save_outputs(transcript, summary, json_path, output_dir)
  }

  invisible(list(
    segments   = segments,
    transcript = transcript,
    summary    = summary,
    paths      = paths
  ))
}
