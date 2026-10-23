# Isolated comparison targets. Product sources remain unchanged; the fixed
# archive deliberately supplies the complete alternative GrowPatch TU before
# the unmodified current tracer archive. Linkmaps audit archive extraction.
function(vcgrow_add_verification_targets)
  find_package(Boost CONFIG REQUIRED COMPONENTS program_options)
  if(NOT TARGET vc_core OR NOT TARGET vc_tracer)
    message(FATAL_ERROR "Current complete vc_core/vc_tracer targets required")
  endif()
  add_library(vcgrow_requested_bounds STATIC "${VCGROW_CANDIDATE_FILE}")
  target_include_directories(vcgrow_requested_bounds PRIVATE "${CMAKE_SOURCE_DIR}/libs/edt")
  target_link_libraries(vcgrow_requested_bounds PUBLIC vc_tracer)
  foreach(variant baseline fixed)
    add_executable(vc_grow_seg_from_seed_${variant}
      "${CMAKE_SOURCE_DIR}/apps/src/vc_grow_seg_from_seed.cpp")
    if(variant STREQUAL "fixed")
      target_link_libraries(vc_grow_seg_from_seed_${variant} PRIVATE vcgrow_requested_bounds vc_core Boost::program_options)
    else()
      target_link_libraries(vc_grow_seg_from_seed_${variant} PRIVATE vc_tracer vc_core Boost::program_options)
    endif()
    target_link_options(vc_grow_seg_from_seed_${variant} PRIVATE
      "-Wl,-Map,${CMAKE_BINARY_DIR}/vc_grow_seg_from_seed_${variant}.map")
    if(MINGW AND EXISTS "${VC_UTF8_MANIFEST_RC}")
      target_sources(vc_grow_seg_from_seed_${variant} PRIVATE "${VC_UTF8_MANIFEST_RC}")
      set_property(SOURCE "${VC_UTF8_MANIFEST_RC}" TARGET_DIRECTORY vc_grow_seg_from_seed_${variant}
        PROPERTY OBJECT_DEPENDS "${VC_UTF8_MANIFEST}")
    endif()
  endforeach()
endfunction()
cmake_language(DEFER CALL vcgrow_add_verification_targets)
